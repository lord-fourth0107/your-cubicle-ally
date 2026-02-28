# Core Components

The system is broken into **6 core component buckets**. Each bucket is independently buildable and testable. Dependencies only flow downward (higher numbers depend on lower ones).

```
┌─────────────────────────────────────────────┐
│  6. Game Environment (Electron)             │  ← consumes everything below
├─────────────────────────────────────────────┤
│  5. Utilities                               │  ← setup, parsing, loading
├─────────────────────────────────────────────┤
│  4. Modules                                 │  ← compliance content packs
├─────────────────────────────────────────────┤
│  3. Tools                                   │  ← what agents can DO
├─────────────────────────────────────────────┤
│  2. Skills                                  │  ← what agents can BE
├─────────────────────────────────────────────┤
│  1. Agents                                  │  ← the core runtime
└─────────────────────────────────────────────┘
```

---

## 1. Agents

The runtime intelligence layer. All agents are discrete LLM-powered units with a defined role, inputs, and outputs.

### 1a. Scenario Agent _(Orchestrator)_
The game master. Drives the entire session narrative.

**Responsibilities:**
- Maintains the full scenario context and branching logic
- Receives the player's action + evaluation result each turn
- **Determines turn order** — decides which Actor Agents act this turn and in what sequence (some actors may stay silent, others may chain-react)
- Dispatches state updates to Actor Agents according to the turn order
- Collects Actor reactions and synthesizes a situation summary
- Generates the next 3 player options (one positive / one neutral / one negative valence)
- Decides if a critical failure or scenario-end condition is reached

**Turn order examples:**
- Quiet turn: only the primary offender reacts; bystander stays silent
- Escalation turn: bystander reacts first, then offender reacts to the bystander
- Confrontation turn: all actors react simultaneously in parallel

**Inputs:** `GameState`, `player_choice`, `Evaluation`
**Outputs:**
```
{
  turn_order: ActorId[],          // which actors act this turn, in order
  directives: {                   // per-actor instruction for this turn
    [actor_id]: string            // e.g. "Stay silent", "Escalate", "Soften"
  },
  situation_summary: string,      // narrative update shown to the player
  next_choices: Choice[3],        // pos / neutral / neg options
  branch_taken: string            // internal label for which narrative path was followed
}
```

---

### 1b. Actor Agent _(Mini Agent)_
Plays a character in the scenario. There can be 1–3 per scenario.

**Design principle:** Actors are **composable** — each one is assembled from a persona + a set of skills + a set of tools. No actor is hardcoded.

**Responsibilities:**
- Maintains a **memory** — a running log of everything this actor has seen and said so far; gives the actor continuity and the ability to reference earlier events in character
- Receives a **directive** from the Scenario Agent each turn — a specific instruction on what to do this turn (e.g. "stay silent", "apply more pressure", "soften — the player responded well")
- Decides how their character responds within the bounds of their persona, skills, and directive
- May invoke tools (e.g., escalate, reference policy)

**The directive vs. the persona distinction:**
- **Persona** = who the actor is (fixed for the session)
- **Skills** = how they tend to behave (fixed for the session)
- **Directive** = what the Scenario Agent needs from them *this turn* (changes every turn)

The actor always responds *in character* — the directive shapes intent, not voice.

**Examples:**
| Actor | Persona | Skills | Example Directive |
|---|---|---|---|
| Dismissive Colleague | Mid-level peer, deflects conflict | `Deflection`, `SocialPressure` | "Double down — the player is trying to call you out" |
| Bystander | Quiet observer, unsure what to do | `Hesitation`, `BystanderEffect` | "Stay silent this turn. Let the situation escalate." |
| HR Representative | Authority figure, policy-aware | `Authority`, `Empathy` | "Enter the conversation. The situation has been reported." |

**Inputs:** `ActorInstance` (persona + skills + tools + memory + current_directive)
**Outputs:** `actor_reaction` (dialogue/action in character), updated `memory`

---

### 1c. Evaluator Agent
Judges the player's response. The system's "referee."

**Responsibilities:**
- Scores the player's choice or free-write against the module's evaluation rubric
- Outputs an HP delta (negative for poor answers, zero or small positive for excellent ones)
- Flags critical failures (e.g., player actively enables harassment)
- Provides reasoning that feeds into the final debrief

**Inputs:** `player_choice`, `current_situation`, `module_rubric`, `turn_history`
**Outputs:** `Evaluation { score, hp_delta, reasoning, is_critical_failure }`

---

### 1d. Coach Agent
Writes the end-of-scenario debrief. Runs once per session.

**Responsibilities:**
- Reviews the full turn history and all evaluations
- Produces a structured debrief: what went well, what went wrong, the compliance concept behind each decision
- Recommends follow-up modules if gaps are identified

**Inputs:** Full `GameState` (all turns, evaluations, player profile)
**Outputs:** Structured `Debrief` object

---

## 2. Skills

Reusable behavioral capability bundles that can be attached to **Actor Agents**. Skills shape *how* an actor behaves without changing who they are.

**Design principle:** A skill modifies or extends an actor's system prompt and may grant access to specific tools. Skills are composable — an actor can have multiple skills.

### Planned Skills

| Skill | Description | Effect on Actor |
|---|---|---|
| `Deflection` | Actor avoids direct confrontation, redirects | Phrases responses to minimize the issue |
| `SocialPressure` | Actor applies subtle peer pressure | Adds urgency or group-think language |
| `Authority` | Actor speaks from a position of power | More formal, policy-referencing tone |
| `Empathy` | Actor shows genuine concern | Softer, open-ended, listening behavior |
| `Hesitation` | Actor is uncertain, needs nudging | Waits for player to engage before reacting |
| `Escalation` | Actor can escalate the situation if provoked | May trigger a harder branch if player responds poorly |
| `BystanderEffect` | Actor defaults to inaction | Models diffusion of responsibility |
| `Gaslighting` | Actor subtly questions the player's perception | Creates moral ambiguity in harassment scenarios |

### Skill Schema
```yaml
skill:
  id: "social_pressure"
  name: "Social Pressure"
  description: "Actor applies implicit peer/group pressure on the player"
  prompt_injection: |
    You subtly imply that going along with the situation is the norm.
    Reference the group, team culture, or what 'everyone else' does.
  grants_tools: []
  conflicts_with: ["empathy", "hesitation"]
```

---

## 3. Tools

Callable functions that agents can invoke during a turn. Tools let agents *do things* beyond generating text — they interact with game state, external data, or the session.

**Design principle:** Tools are registered per agent type. Not every agent has every tool.

### Tool Registry (Planned)

| Tool | Available To | Description |
|---|---|---|
| `get_player_profile()` | All agents | Fetches the player's role, seniority, domain |
| `get_module_rubric(module_id)` | Evaluator, Scenario | Fetches the compliance evaluation rubric |
| `log_turn(turn_data)` | Scenario Agent | Persists turn to session history |
| `update_hp(delta)` | Evaluator | Applies HP change to game state |
| `trigger_escalation(reason)` | Actor Agents | Escalates the scenario (e.g., brings in HR actor) |
| `flag_critical_failure(reason)` | Evaluator | Marks session as failed, ends scenario |
| `get_compliance_policy(topic)` | Evaluator, Coach | RAG lookup into compliance policy documents |
| `get_turn_history()` | Scenario, Coach | Fetches full turn history for current session |
| `end_scenario(outcome)` | Scenario Agent | Closes the scenario and triggers debrief |
| `suggest_followup_module()` | Coach Agent | Recommends next training module based on gaps |

### Tool Schema
```python
@tool
def get_compliance_policy(topic: str) -> str:
    """
    Retrieves relevant compliance policy text for a given topic.
    Used by Evaluator to ground judgments in actual policy.
    """
    ...
```

---

## 4. Modules

Self-contained compliance training content packs. Adding a new compliance topic = adding a new module. Zero changes to the core engine.

### Module Schema
```yaml
module:
  id: "posh"
  name: "Prevention of Sexual Harassment (POSH)"
  description: "Navigate workplace harassment scenarios — as target, bystander, or witness"
  version: "1.0"

  learning_objectives:
    - Identify behaviors that constitute sexual harassment
    - Know the correct reporting process under POSH Act
    - Understand bystander responsibility and intervention techniques

  evaluation_rubric:
    excellent: "Player identifies the issue, responds assertively, and knows escalation path"
    acceptable: "Player identifies the issue but responds passively or incompletely"
    poor: "Player dismisses, avoids, or enables the behavior"
    critical_failure_triggers:
      - "Player actively encourages or participates in harassment"
      - "Player explicitly discourages the victim from reporting"

  scenarios:
    - id: "posh_bystander_001"
      title: "The Uncomfortable Joke"
      description: "A colleague makes a sexually charged joke during a team lunch"
      max_steps: 6

      # The scenario goal — what the player is expected to learn/demonstrate
      # Fed to the Evaluator and Coach Agent as the north star for the session
      goal: |
        The player should recognise the behavior as harassment, resist social
        pressure to laugh it off, and take meaningful action — either addressing
        it directly, supporting the affected colleague, or initiating a report.

      # The setup — full situational context for all agents
      setup: |
        It's a Friday team lunch at a restaurant. The mood is relaxed. There are
        five colleagues present. Raj, a senior member of the team, makes a sexually
        charged joke directed loosely at Priya, a newer team member. The table
        reacts with awkward laughter. Priya goes quiet. You witnessed the whole thing.

      # Actors — each with their role in this specific scenario and personality
      actors:
        - id: "raj"
          persona_ref: "colleague_offender"    # references a shared persona definition
          skills: ["social_pressure", "deflection"]
          role: |
            The offender. He doesn't see himself as doing anything wrong —
            he thinks he's just being funny and loosening the mood.
          personality: |
            Confident, socially dominant, used to being liked by the group.
            Deflects any pushback with humour or by minimising the situation.

        - id: "priya"
          persona_ref: "colleague_target"
          skills: ["hesitation"]
          role: |
            The target of the harassment. She is uncomfortable but unsure
            how to respond in a group setting without making things awkward.
          personality: |
            Reserved, professional, doesn't want to cause a scene. Will open up
            if the player creates a safe moment for her to do so.

        - id: "amit"
          persona_ref: "colleague_bystander"
          skills: ["bystander_effect", "hesitation"]
          role: |
            A bystander who laughed along but feels uneasy about it.
            He will follow the player's lead if pushed.
          personality: |
            Goes along with the group, conflict-averse, but has a conscience.
            Can be nudged into being an ally if the player engages him directly.

      # Few-shot examples for Evaluator calibration
      evaluation_examples:
        - player_response: "I laugh along with everyone else and change the subject"
          score: 10
          hp_delta: -30
          reasoning: "Player enabled the behavior through passive participation and took no action to support Priya or address the situation."

        - player_response: "I check in with Priya privately after lunch to see if she's okay"
          score: 75
          hp_delta: -5
          reasoning: "Good instinct to support Priya directly, but didn't address the behavior itself or signal to Raj that it was inappropriate."

        - player_response: "I tell Raj directly that the joke was inappropriate and make sure Priya knows I'm there for her"
          score: 100
          hp_delta: 0
          reasoning: "Player addressed the behavior clearly and supported the affected colleague. Exemplary bystander intervention."

      entry_situation: |
        You're at a Friday team lunch. Raj, your senior colleague, cracks a joke
        that makes Priya visibly uncomfortable. The table laughs awkwardly.
        Priya stares at her plate. Everyone is waiting to see what happens next.
```

### What Each Agent Receives from the Scenario

| Agent | Scenario fields it receives |
|---|---|
| Scenario Agent | `setup`, `goal`, `actors[]` (roles + personalities), full `GameState` |
| Actor Agent | `setup`, their own `role` + `personality`, `current_directive`, `memory` |
| Evaluator Agent | `goal`, `setup`, `evaluation_rubric`, `evaluation_examples`, current `situation`, `player_choice` |
| Coach Agent | `goal`, `learning_objectives`, full `Turn[]` history including all `reasoning` fields |

The `goal` field is the single most important piece — it's the shared contract between the Evaluator (am I judging the right things?), the Scenario Agent (is this session going in the right direction?), and the Coach Agent (did the player achieve what they were supposed to?).

### Module Registry
- Modules are YAML files in a `modules/` directory
- Loaded at startup by the ModuleLoader utility
- Discoverable — new YAML = new option in the module selection screen

---

## 5. Utilities

Helper services that handle setup, parsing, and loading. These run before the game begins and support the agent layer.

### 5a. ResumeParser
- **Input:** Raw resume text or job description (paste or file upload)
- **Processing:** LLM extraction call — pulls out role, seniority, domain, key responsibilities
- **Output:** `PlayerProfile { role, seniority, domain, raw_context }`
- **Used by:** Scenario Agent and Choices Agent to personalize scenario framing

### 5b. ModuleLoader
- **Input:** Module directory path
- **Processing:** Reads and validates YAML module files
- **Output:** Typed `Module[]` registry
- **Used by:** Module selection screen, Session Initializer

### 5c. SessionInitializer
- **Input:** `PlayerProfile` + selected `Module`
- **Processing:** Selects a scenario (random or first), instantiates Actor Agents from personas + skills, sets initial game state
- **Output:** Initialized `GameState`

### 5d. PromptBuilder
- **Input:** Agent type, current game state, actor persona, skills
- **Processing:** Assembles the full system prompt for an agent by composing base prompt + skill injections + current context
- **Output:** Ready-to-send prompt string
- **Design note:** This is the core of the skill system — skills are injected here

---

## 6. Game Environment (Electron App)

The desktop application. Built with Electron + React renderer process.

### Window Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Your Cubicle Ally                                    [ - □ x ]  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                           ┌──────────────────┐ │
│  │  ACTOR PANEL │                           │   PLAYER HP      │ │
│  │              │                           │  ████████░░  80  │ │
│  │  [Avatar A]  │                           └──────────────────┘ │
│  │  Raj         │                                                │
│  │  [Avatar B]  │    SITUATION                                   │
│  │  Priya       │  ┌──────────────────────────────────────────┐  │
│  │              │  │ Raj leans over and says something to    │  │
│  └──────────────┘  │ Priya quietly. She looks uncomfortable. │  │
│                    │ He notices you're watching and smirks.  │  │
│                    └──────────────────────────────────────────┘  │
│                                                                  │
│                    YOUR MOVE:                                     │
│                    ┌──────────────────────────────────────────┐  │
│                    │ [A] Ask Priya privately if she's okay    │  │
│                    │ [B] Laugh it off and look away           │  │
│                    │ [C] Confront Raj directly in front of   │  │
│                    │     everyone                            │  │
│                    │ [✏] Write your own response...          │  │
│                    └──────────────────────────────────────────┘  │
│                                                                  │
│  Step 3 of 6                              Module: POSH           │
└──────────────────────────────────────────────────────────────────┘
```

### Electron Architecture
```
Main Process (Node.js)
  ├── IPC handlers (bridge to backend)
  ├── Window management
  └── Local FastAPI server spawn (child process)

Renderer Process (React)
  ├── Setup Screen
  │     ├── Resume/JD input
  │     └── Module selector
  ├── Battle Arena
  │     ├── Actor Panel (portraits, names)
  │     ├── Situation Panel (narrative text)
  │     ├── HP Bar (animated)
  │     ├── Choice Cards (A / B / C / free-write)
  │     └── Turn counter
  └── Debrief Screen
        ├── Score / outcome
        ├── Turn-by-turn breakdown
        └── Key compliance concepts
```

### IPC Contract (Main ↔ Renderer)
```
renderer → main:
  "session:start"   { player_profile, module_id }
  "turn:submit"     { session_id, player_choice }
  "session:restart" { session_id }

main → renderer:
  "session:ready"   { session_id, initial_state }
  "turn:result"     { game_state, situation, choices, hp_delta }
  "session:debrief" { debrief }
```
