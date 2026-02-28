"""
utilities/prompt_builder.py
---------------------------
Assembles prompts for all agents.

Actor prompts are split into two parts:
  - build_actor_system_prompt() — STATIC, set once as system_instruction at actor init.
  - Dynamic turn message — ActorAgent constructs it inline.

Owner: Utilities team
Depends on: skills/skill_registry, core/game_state
Depended on by: all agent classes
"""

from skills.skill_registry import SkillRegistry
from core.game_state import ActorInstance


class PromptBuilder:
    def __init__(self, skill_registry: SkillRegistry):
        self.registry = skill_registry

    def build_actor_system_prompt(self, actor: ActorInstance, scenario_context: dict) -> str:
        """Build the STATIC system prompt for an Actor Agent."""
        parts = [
            f"You are playing a character in a workplace compliance training scenario.",
            "",
            f"[PERSONA] {actor.persona}",
            f"[ROLE] {actor.role}",
            f"[PERSONALITY] {actor.personality}",
        ]
        for skill_id in actor.skills:
            try:
                skill = self.registry.get(skill_id)
                parts.append(f"\n[SKILL: {skill.name}]\n{skill.prompt_injection}")
            except KeyError:
                pass
        parts.append("\n[SCENARIO] This is an interactive compliance simulation.")
        parts.append("Stay in character. Respond briefly (1-3 sentences).")
        return "\n".join(parts)

    def build_evaluator_prompt(self, scenario_context: dict, turn_history: list) -> str:
        """Build the system prompt for the Evaluator Agent."""
        module_id = scenario_context.get("module_id", "posh")
        actors = scenario_context.get("actors", [])
        def _ar(a): return a.get("actor_id", "") if isinstance(a, dict) else getattr(a, "actor_id", "")
        def _rr(a): return (a.get("role", "") if isinstance(a, dict) else getattr(a, "role", ""))[:40]
        actor_summary = ", ".join(f"{_ar(a)} ({_rr(a)}...)" for a in (actors[:5] if actors else []))
        def _th(t, i):
            step = t.get("step", i) if isinstance(t, dict) else getattr(t, "step", i)
            choice = t.get("player_choice", "") if isinstance(t, dict) else getattr(t, "player_choice", "")
            delta = t.get("hp_delta", 0) if isinstance(t, dict) else getattr(t, "hp_delta", 0)
            return f"Step {step}: {choice or '(entry)'} | HP delta: {delta}"
        history_summary = "\n".join(_th(t, i) for i, t in enumerate(turn_history[:10]))
        return (
            f"You evaluate player choices in a {module_id} compliance scenario.\n"
            f"Actors: {actor_summary}\n"
            f"Turn history so far:\n{history_summary}\n\n"
            "Score 0-100. HP delta: 0 (neutral), -5 to -15 (minor lapse), -20 to -40 (serious). "
            "is_critical_failure=true only for egregious violations."
        )

    def build_scenario_prompt(self, scenario_context: dict, turn_history: list) -> str:
        """Build the system prompt for the Scenario Agent."""
        actors = scenario_context.get("actors", [])
        def _ar(a): return a.get("actor_id", "") if isinstance(a, dict) else getattr(a, "actor_id", "")
        def _rr(a): return (a.get("role", "") if isinstance(a, dict) else getattr(a, "role", ""))[:60]
        actor_list = "\n".join(f"- {_ar(a)}: {_rr(a)}" for a in actors)
        def _th(t, i):
            step = t.get("step", i) if isinstance(t, dict) else getattr(t, "step", i)
            sit = (t.get("situation", "") if isinstance(t, dict) else getattr(t, "situation", ""))[:80]
            choice = t.get("player_choice", "") if isinstance(t, dict) else getattr(t, "player_choice", "")
            return f"Step {step}: situation={sit}... | choice={choice or '(entry)'}"
        history_summary = "\n".join(_th(t, i) for i, t in enumerate(turn_history[-5:]))
        return (
            f"You are the game master for a workplace compliance scenario.\n"
            f"Actors (use these actor_ids in turn_order and directives):\n{actor_list}\n\n"
            f"Recent history:\n{history_summary}\n\n"
            "Advance the narrative. turn_order: who speaks this turn (actor_ids). "
            "directives: short instruction per actor. situation_summary: 2-4 sentences. "
            "next_choices: exactly 3 options (positive/neutral/negative valence). branch_taken: short label."
        )
