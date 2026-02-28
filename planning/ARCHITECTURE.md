# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GAME ENVIRONMENT (Electron App)                  │
│                                                                     │
│   [Setup Screen]  ──►  [Battle Arena]  ──►  [Debrief Screen]       │
│                                                                     │
│   - Player HP bar          - Actor portraits / chat bubbles         │
│   - Situation panel        - 3 action cards (pos/neg/neutral)       │
│   - Free-write input       - Turn-by-turn narrative feed            │
└────────────────────────────┬────────────────────────────────────────┘
                             │  IPC / local API
┌────────────────────────────▼────────────────────────────────────────┐
│                         BACKEND (local or server)                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     UTILITIES LAYER                         │    │
│  │  ResumeParser  │  ModuleLoader  │  SessionInitializer       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │               GAME STATE (Session Manager)                  │    │
│  │  player_profile | active_module | active_scenario           │    │
│  │  actors[] | current_step | player_hp | turn_history[]       │    │
│  └───────────────────────────┬─────────────────────────────────┘    │
│                              │                                      │
│  ┌───────────────────────────▼─────────────────────────────────┐    │
│  │                  AGENT ORCHESTRATION LAYER                  │    │
│  │                                                             │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │              SCENARIO AGENT (Orchestrator)           │   │    │
│  │  │  - Drives the narrative                             │   │    │
│  │  │  - Dispatches updates to actors per turn order       │   │    │
│  │  │  - Generates 3 options: positive / neutral / neg    │   │    │
│  │  │  - Decides how scenario branches after player acts  │   │    │
│  │  └──────────────┬──────────────────────────────────────┘   │    │
│  │                 │  state broadcast                          │    │
│  │     ┌───────────▼──────────────────────────┐               │    │
│  │     │         ACTOR AGENTS (1–3)            │               │    │
│  │     │                                      │               │    │
│  │     │  Actor A         Actor B   Actor C   │               │    │
│  │     │  [persona]       [persona] [persona] │               │    │
│  │     │  [skills[]]      [skills[]] [skills[]]│              │    │
│  │     │  [tools[]]       [tools[]] [tools[]] │               │    │
│  │     │                                      │               │    │
│  │     │  Each actor receives scenario update  │               │    │
│  │     │  and decides their reaction/dialogue  │               │    │
│  │     └──────────────────────────────────────┘               │    │
│  │                                                             │    │
│  │  ┌─────────────────┐      ┌──────────────────────────┐     │    │
│  │  │ Evaluator Agent │      │      Coach Agent          │     │    │
│  │  │ Judges player   │      │  Writes end debrief       │     │    │
│  │  │ response → HP Δ │      │  from full turn history   │     │    │
│  │  └─────────────────┘      └──────────────────────────┘     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     MODULE REGISTRY                         │    │
│  │    POSH | Security | Data Privacy | Code of Conduct | ...   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Context Model

Every agent operates from one or both of two context layers:

```
┌──────────────────────────────────────────────────────┐
│                  SHARED CONTEXT                      │
│  scenario goal + setup | player profile              │
│  actor roster (names, roles, personalities)          │
│  full turn history (situations, choices, reactions,  │
│  evaluations) | module rubric                        │
│                                                      │
│  Read by: Scenario Agent, Evaluator, Coach Agent     │
│           and Actor Agents (as grounding)            │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│            PER-ACTOR HISTORY (one per actor)         │
│  This actor's own dialogue across all turns          │
│  Maintained as a Gemini ChatSession                  │
│                                                      │
│  Read by: Actor Agents only                          │
└──────────────────────────────────────────────────────┘
```

**What each agent sees:**

| Agent | Shared Context | Per-Actor History |
|---|---|---|
| Scenario Agent | ✅ Full | ✗ |
| Actor Agent | ✅ As grounding | ✅ Own history only |
| Evaluator Agent | ✅ Full + module rubric | ✗ |
| Coach Agent | ✅ Full | ✗ |

**HP rule:** Drain only — bad answers reduce HP, good answers do not recover it. Max penalty per turn is -40. Gradient scoring: hp_delta scales proportionally to the 0–100 score.

**Actor cap:** Maximum 3 Actor Agents per scenario.

---

## The Multi-Actor Model

### Key Insight
A scenario isn't a 1v1 — it's a room. There are 1–3 **Actor Agents** playing characters (a colleague, a manager, a bystander, a threat actor). The player navigates the whole room, not just one opponent.

### Scenario Agent as Orchestrator
The Scenario Agent is the "game master":
1. It knows the full game state and scenario script
2. After each player action, it **determines turn order** — which Actor Agents act this turn, and in what sequence
3. It dispatches state updates to Actor Agents one at a time (or in parallel) per the turn order it set
4. Each Actor Agent independently decides how their character reacts
5. The Scenario Agent **collects** actor reactions and weaves them into the next situation
6. It generates the next 3 options for the player (one positive/compliant, one neutral/ambiguous, one negative/non-compliant)

Turn order is dynamic — the Scenario Agent may decide only one actor is relevant this turn, or all three react in sequence, or they react simultaneously. This allows for natural-feeling scenes where some characters stay silent while others escalate.

### Actor Agents
Each Actor Agent is a **mini agent** with:
- A **persona** (system prompt defining who they are in this scenario)
- A set of **skills** (reusable behavioral capabilities)
- A set of **tools** (function calls they can invoke)
- They are fully **composable** — actors are assembled from skills, not hardcoded

---

## Turn Data Flow

```
Player submits choice (or free-write)
           │
           ▼
  ┌─────────────────────┐
  │  Evaluator Agent    │  ← judges quality vs. module rubric
  │  → score, hp_delta  │
  │  → reasoning        │
  └──────────┬──────────┘
             │
             ▼
  ┌─────────────────────────────────────────────┐
  │              Scenario Agent                 │
  │  Receives: player_choice + evaluation       │
  │  1. Decides narrative branch                │
  │  2. Determines turn order for this turn     │
  │     (which actors act, in what sequence)    │
  │  3. Dispatches state updates per turn order │
  │  4. Collects Actor reactions                │
  │  5. Generates next situation summary        │
  │  6. Generates next 3 options                │
  └─────────────────────────────────────────────┘
             │
     turn order determined by Scenario Agent
     e.g. [Actor B silent] → [Actor A reacts] → [Actor C escalates]
             │
     ┌───────┴───────┐
     ▼               ▼
Actor Agent A    Actor Agent C   (only these two act this turn)
Reacts in        Escalates in
character        character
     └───────┬───────┘
             ▼
  Session Manager updates GameState
  (new Turn recorded, HP updated)
             │
             ▼
  Electron UI renders next turn
```

---

## GameState Shape

```
GameState {
  session_id: string
  player_profile: PlayerProfile
  module_id: string             // references a module in the registry
  scenario_id: string           // references a scenario within the module
  actors: ActorInstance[]       // active Actor Agents for this scenario
  current_step: number
  max_steps: number
  player_hp: number             // starts at 100
  history: Turn[]
  status: "active" | "won" | "lost"
                                // won = all steps done with HP > 0 → debrief
                                // lost = HP hit 0 or critical failure → retry or debrief
}

ActorInstance {
  actor_id: string
  persona: string               // who this actor is (base character definition)
  role: string                  // their function in this specific scenario
  personality: string           // behavioral traits for this scenario
  skills: string[]              // skill ids — resolved to Skill objects by SkillRegistry
  tools: string[]               // tool ids — resolved at runtime
  memory: Message[]             // this actor's dialogue history (synced from ChatSession)
  current_directive: string     // set by Scenario Agent each turn
                                // e.g. "Stay quiet, let Actor B escalate first"
                                //      "Apply more pressure — the player is avoiding the issue"
                                //      "Soften slightly — the player responded well"
}

Turn {
  step: number
  situation: string             // Scenario Agent's narrative update
  turn_order: ActorId[]              // which actors acted this turn, in sequence
  directives: { [actor_id]: string } // what the Scenario Agent told each actor to do
  actor_reactions: ActorReaction[]   // each acting actor's response this turn
  choices_offered: Choice[]          // 3 options: positive / neutral / negative
  player_choice: string              // empty string on the entry turn (no player action yet)
  evaluation: Evaluation | null      // null on the entry turn
  hp_delta: number
  narrative_branch: string      // which branch the scenario took
}

Choice {
  label: string
  valence: "positive" | "neutral" | "negative"
}

Evaluation {
  score: number                 // 0–100
  hp_delta: number
  reasoning: string
  is_critical_failure: boolean
}
```

---

## Tech Stack

| Layer | Choice | Status | Notes |
|---|---|---|---|
| Game Environment | Electron + React | ✅ Confirmed | Desktop app; renderer process for all UI |
| Backend | Python / FastAPI | ✅ Confirmed | Spawned as child process by Electron main; renderer calls localhost HTTP |
| Agent Framework | google-generativeai SDK | ✅ Confirmed | Direct Gemini SDK — ChatSession for actor memory, JSON mode for structured outputs |
| LLM | Google Gemini Flash | ✅ Confirmed | Fast, cost-efficient; used for all agent calls via google-generativeai SDK |
| State | In-memory (session) + SQLite | 🟡 Leaning | SQLite fits local Electron deployment; no external DB needed |
| Module Definitions | YAML files | ✅ Confirmed | Bundled with app, version-controlled, authorable by non-devs |
| Packaging | PyInstaller + Electron Builder | 🟡 Leaning | Bundle frozen Python binary alongside Electron app |

---

## Extension Points

- **More actors per scenario** — just add another ActorInstance; engine handles N actors
- **New skills** — drop a new skill definition; any actor can pick it up
- **New modules** — new YAML file in the module registry; zero core changes
- **Multiplayer** — multiple players in the same scenario room (future)
- **Manager view** — Electron window or web dashboard showing aggregated debrief results
- **Voice** — swap text input/output for speech; actors speak in character
