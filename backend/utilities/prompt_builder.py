"""
utilities/prompt_builder.py
---------------------------
Assembles prompts for all agents.

Actor prompts are split into two parts:
  - build_actor_system_prompt() — STATIC, set once as system_instruction at actor init.
      Contains: persona, role, personality, skill injections, scenario goal + setup.
  - Dynamic turn message — NOT built here. ActorAgent constructs it inline:
      "Situation: ...\nYour directive: ..."

All other agents (Evaluator, Scenario, Coach) use single-call prompts
assembled by their respective build_*_prompt() methods.

Skill injection strategy:
  Skills are appended after personality, each clearly delimited.

Owner: Utilities team
Depends on: skills/skill_registry, utilities/module_loader, core/game_state
Depended on by: all agent classes
"""

from skills.skill_registry import SkillRegistry
from core.game_state import ActorInstance
from utilities.module_loader import ModuleLoader, ScenarioData


def _format_turn_history(turn_history: list) -> str:
    if not turn_history:
        return "  (no turns yet)"
    lines = []
    for t in turn_history:
        line = f"  Step {t.step}: situation=\"{t.situation[:120]}...\""
        if t.player_choice:
            line += f" | player_choice=\"{t.player_choice}\""
        if t.evaluation:
            line += f" | score={t.evaluation.score} hp_delta={t.evaluation.hp_delta}"
        lines.append(line)
    return "\n".join(lines)


def _narrative_arc_phase(current_step: int, max_steps: int) -> str:
    """
    Map the current step to a named narrative arc phase.

    Phase boundaries (example for max_steps=6):
      Step 0 → entry (not a player turn)
      Step 1 → OPENING
      Step 2 → OPENING
      Step 3 → MID
      Step 4 → ESCALATION
      Step 5 → CLOSING   (penultimate — one more turn after this)
      Step 6 → FINAL     (this is the last player action, session ends after)

    The general rule:
      - First ~33 % of steps → OPENING
      - Middle ~33 %        → MID / ESCALATION
      - Second-to-last step → CLOSING
      - Last step           → FINAL

    Note: process_turn is called with current_step values 0..(max_steps-1).
    After the call with current_step = max_steps-1, apply_turn increments the
    counter to max_steps → session ends. So steps_remaining=1 IS the final turn.
    """
    steps_remaining = max_steps - current_step  # how many player actions remain including this one
    if steps_remaining <= 1:
        return "FINAL"
    if steps_remaining == 2:
        return "CLOSING"
    midpoint = max_steps // 2
    if current_step <= midpoint // 2:
        return "OPENING"
    if current_step <= midpoint:
        return "MID"
    return "ESCALATION"


class PromptBuilder:
    def __init__(self, skill_registry: SkillRegistry, module_loader: ModuleLoader):
        self.registry = skill_registry
        self.loader = module_loader

    def _load_scenario(self, scenario_context: dict) -> ScenarioData:
        return self.loader.load_scenario(
            module_id=scenario_context["module_id"],
            scenario_id=scenario_context["scenario_id"],
        )

    def build_actor_system_prompt(self, actor: ActorInstance, scenario_context: dict) -> str:
        """
        Build the STATIC system prompt for an Actor Agent.
        Called once at session start, set as system_instruction on the GenerativeModel.

        Structure:
          [PERSONA]           — who the actor is
          [ROLE]              — their function in this scenario
          [PERSONALITY]       — how they behave
          [SKILLS]            — injected prompt fragments from each assigned skill
          [SCENARIO CONTEXT]  — scenario goal + opening situation
          [RULES]             — hard behavioural constraints
        """
        scenario = self._load_scenario(scenario_context)

        # Skill injections
        skill_blocks = []
        for skill_id in actor.skills:
            try:
                skill = self.registry.get(skill_id)
                skill_blocks.append(
                    f"--- SKILL: {skill.name} ---\n{skill.prompt_injection.strip()}"
                )
            except KeyError:
                pass  # unknown skill — skip gracefully

        skills_section = (
            "\n\n".join(skill_blocks)
            if skill_blocks
            else "No special behavioural skills assigned."
        )

        entry_situation = scenario.entry_turn.situation.strip()

        return f"""\
You are playing the character {actor.actor_id!r} in a workplace compliance training simulation.
This is a roleplay exercise designed to help employees develop bystander intervention skills.

[PERSONA]
{actor.persona.strip()}

[ROLE IN THIS SCENARIO]
{actor.role.strip()}

[PERSONALITY]
{actor.personality.strip()}

[BEHAVIOURAL SKILLS]
{skills_section}

[SCENARIO CONTEXT]
Training goal: {scenario.rubric.goal.strip()}
Opening situation: {entry_situation}

[OUTPUT FORMAT — FOLLOW EXACTLY]
Each response must use this format:

  [optional internal thought or feeling in square brackets] Spoken words out loud.

Rules:
- Spoken words are what your character actually says aloud. Write them as natural, realistic dialogue.
- Square brackets [ ] are for a brief internal thought, feeling, or physical reaction — not narration.
  Only include brackets if they add meaningful character insight. They are optional.
- NEVER write in third person. NEVER narrate ("She picks at her salad", "He grins").
- NEVER use quotation marks — the spoken words ARE the dialogue.
- 1–3 sentences total (brackets + spoken). Keep it tight and natural.

Good examples:
  [Caught off guard, heart sinking.] Come on, it was just a joke — everyone needs to relax.
  [Not sure whether to laugh or not.] Yeah... anyway, should we order?
  [I want to disappear right now.] Let's just have a nice lunch.

Bad examples (do NOT do this):
  My smile falters as I stare at my plate, hoping no one notices my discomfort. (narration — wrong)
  "Let's just have a nice lunch." (quotation marks — wrong)
  She fiddles with her napkin. (third person — wrong)

[ABSOLUTE RULES]
- Always stay in character as {actor.actor_id}.
- Never acknowledge that this is a training simulation or break the fourth wall.
- Your directive shapes your intent each turn, but your voice and personality stay constant.
""".strip()

    def build_evaluator_prompt(self, scenario_context: dict, turn_history: list) -> str:
        """
        Build the system prompt for the Evaluator Agent.

        Includes: scenario goal, actor roster, rubric, few-shot examples, turn history.
        """
        scenario = self._load_scenario(scenario_context)

        # Actor roster summary
        actors = scenario_context.get("actors", [])
        roster_lines = [
            f"  - {a['actor_id']}: {a['role']}"
            for a in actors
        ]
        roster = "\n".join(roster_lines) if roster_lines else "  (no actors)"

        # Rubric key concepts
        concepts = "\n".join(
            f"  - {c}" for c in scenario.rubric.key_concepts
        )

        # Few-shot examples
        example_blocks = []
        for ex in scenario.rubric.few_shot_examples:
            example_blocks.append(
                f'  Choice: "{ex.choice}"\n'
                f"  Score: {ex.score}/100\n"
                f"  Reasoning: {ex.reasoning.strip()}"
            )
        examples_section = "\n\n".join(example_blocks)

        history_text = _format_turn_history(turn_history)

        current_situation = (
            turn_history[-1].situation if turn_history else "Scenario has not yet started."
        )

        player_hp = scenario_context.get("player_hp", 100)
        current_step = scenario_context.get("current_step", 0)
        max_steps = scenario_context.get("max_steps", 6)
        arc_phase = _narrative_arc_phase(current_step, max_steps)

        final_turn_note = (
            "\n[FINAL TURN NOTE]\n"
            "This is the player's last action. Weight this choice accordingly — "
            "a final failure to act carries more cost than an early passive turn. "
            "A final proactive choice (especially involving HR or formal reporting) "
            "is the gold standard and should score 90–100."
            if arc_phase in ("FINAL", "CLOSING") else ""
        )

        return f"""\
You are an objective compliance evaluator for a workplace harassment prevention training scenario.
Your job is to score the player's bystander intervention choices against the scenario rubric.
Be fair, consistent, and grounded in real compliance principles.

[SCENARIO GOAL]
{scenario.rubric.goal.strip()}

[ACTOR ROSTER]
{roster}

[KEY COMPLIANCE CONCEPTS]
{concepts}

[EVALUATION RUBRIC — FEW-SHOT EXAMPLES]
{examples_section}

[CURRENT STATE]
Step: {current_step} of {max_steps} (arc phase: {arc_phase})
Player HP: {player_hp}/100
Current situation: {current_situation.strip()[:300]}

[TURN HISTORY]
{history_text}
{final_turn_note}
[SCORING GUIDANCE]
- Score 80–100: Player directly addresses the behaviour, supports the target, or escalates correctly.
- Score 50–79: Player takes partial action — supportive but incomplete, or indirect.
- Score 20–49: Player avoids the situation, deflects, or takes a neutral/passive stance.
- Score 0–19: Player endorses or amplifies the harmful behaviour.
- hp_delta: Derive from score. Score ≥80 → 0 to +10. Score 50–79 → -5 to -15. Score 20–49 → -15 to -25. Score <20 → -25 to -40.
- is_critical_failure: true only if the player actively makes the situation worse (e.g. joins in, intimidates Claire, prevents reporting).
- reasoning: 1–2 concise sentences grounding the score in compliance principles. Avoid jargon.
""".strip()

    def build_scenario_prompt(self, scenario_context: dict, turn_history: list) -> str:
        """
        Build the system prompt for the Scenario Agent.

        Includes: scenario goal, actor roster with personalities, turn history,
        narrative arc phase with step-specific de-escalation guidance.
        """
        scenario = self._load_scenario(scenario_context)

        # Full actor roster with personality detail
        actors = scenario_context.get("actors", [])
        actor_blocks = []
        for a in actors:
            actor_blocks.append(
                f"  {a['actor_id']}:\n"
                f"    Role: {a['role']}\n"
                f"    Personality: {a['personality']}\n"
                f"    Skills: {', '.join(a['skills']) if a['skills'] else 'none'}"
            )
        actor_section = "\n\n".join(actor_blocks) if actor_blocks else "  (no actors)"

        history_text = _format_turn_history(turn_history)

        current_step = scenario_context.get("current_step", 0)
        max_steps = scenario_context.get("max_steps", 6)
        player_hp = scenario_context.get("player_hp", 100)
        steps_remaining = max_steps - current_step
        arc_phase = _narrative_arc_phase(current_step, max_steps)

        # Phase-specific instructions for the Scenario Agent
        if arc_phase == "FINAL":
            arc_guidance = f"""\
⚠ FINAL TURN ({current_step} of {max_steps}) — THE SCENARIO ENDS AFTER THIS TURN.

situation_summary:
  Write a RESOLUTION, not a new conflict. Show the lasting impact of the player's choices
  across the whole scenario. What is Claire's state? Did Marcus face any consequence?
  How does the group dynamic feel? Be specific and consequential — this is the last image
  the player carries away.

turn_order / directives:
  Include 1–2 actors giving brief CLOSING reactions. Direct them toward resolution:
  e.g. Claire expresses how she feels, Jordan reflects on what happened.
  Do NOT introduce new conflict or new characters.

next_choices:
  Still required by the output format but will NOT be shown to the player.
  Generate 3 placeholder closing choices (they will be discarded)."""

        elif arc_phase == "CLOSING":
            arc_guidance = f"""\
CLOSING TURN ({current_step} of {max_steps}) — one turn before the final scene.

Begin de-escalating. The situation should feel like it is moving toward a conclusion.
- Do NOT introduce new characters or escalate the conflict further.
- Directives should start moving actors toward resolution or consequence.
- Choices must be clearly distinguishable:
    positive  = gold-standard bystander move (e.g. escalating to HR, making a direct statement)
    neutral   = partial action with clear limitations
    negative  = a visible missed opportunity with a real cost"""

        elif arc_phase == "OPENING":
            arc_guidance = f"""\
OPENING TURN ({current_step} of {max_steps}) — {steps_remaining} turns remaining.

The situation is still developing. Keep the tone exploratory.
- Choices should be somewhat ambiguous — the player is still finding their footing.
    positive  = clearly supportive, but not dramatic
    negative  = passive or deflecting, not actively harmful
- Directives should keep actors watchful and reactive.
- Deepen the existing conflict naturally; do not introduce unrelated threads."""

        elif arc_phase == "MID":
            arc_guidance = f"""\
MID-GAME TURN ({current_step} of {max_steps}) — {steps_remaining} turns remaining.

Stakes are becoming clearer. The player's pattern of choices should start to matter.
- Choices should be clearly distinguishable:
    positive  = directly addresses the behaviour or supports Claire
    negative  = visible missed opportunity
- Actors should respond realistically to what the player has done so far.
- The situation can escalate if the player has been passive, or stabilise if they have intervened."""

        else:  # ESCALATION
            arc_guidance = f"""\
ESCALATION TURN ({current_step} of {max_steps}) — {steps_remaining} turns remaining.

Tension is near its peak. The consequences of the player's earlier choices are visible.
- Choices should feel high-stakes and consequential.
    positive  = active, specific intervention (name the behaviour, offer Claire support)
    negative  = inaction that clearly leaves Claire worse off
- Actors should be reacting to the cumulative pattern of play, not just this single turn.
- This is the last chance to escalate before the scenario begins wrapping up."""

        return f"""\
You are the game master (Scenario Agent) for a workplace compliance training simulation.
Your job is to advance the narrative after each player action, set directives for each actor,
and generate the next set of 3 player choices.

[SCENARIO GOAL]
{scenario.rubric.goal.strip()}

[ACTOR ROSTER]
{actor_section}

[KEY COMPLIANCE CONCEPTS]
{chr(10).join(f"  - {c}" for c in scenario.rubric.key_concepts)}

[CURRENT STATE]
Step {current_step} of {max_steps} | {steps_remaining} turn(s) remaining | Player HP: {player_hp}/100

[TURN HISTORY]
{history_text}

[NARRATIVE ARC — INSTRUCTIONS FOR THIS TURN]
{arc_guidance}

[OUTPUT RULES — ALWAYS APPLY]
- turn_order: list of actor_ids who react this turn (0–3 actors). Can be empty [] on the final turn.
- directives: for each actor in turn_order, a brief behavioural intent (not dialogue).
- situation_summary: 2–4 sentences written from the player's perspective. Vivid, specific.
  No player choices embedded in the text. Must reflect the arc guidance above.
- next_choices: exactly 3 objects — one each of "positive", "neutral", "negative" valence.
  Each must be a realistic, specific action for a professional workplace context.
- branch_taken: a short snake_case label for this narrative branch (debugging only).

Build on what has happened before. Stay grounded in the workplace setting.
""".strip()
