# Contributing

This project is built in parallel across multiple workstreams. Read this before writing any code.

## What's Already Built

The backend is largely functional. Before starting, check whether your workstream already has implemented code:

| Component | Status |
|---|---|
| `core/game_state.py` | ✅ Complete |
| `core/session_manager.py` | ✅ Complete |
| `core/orchestrator.py` | ✅ Complete |
| `agents/scenario_agent.py` | ✅ Complete |
| `agents/actor_agent.py` | ✅ Complete |
| `agents/evaluator_agent.py` | ✅ Complete |
| `agents/coach_agent.py` | ✅ Complete |
| `agents/guardrail_agent.py` | ✅ Complete |
| `skills/skill_registry.py` | ✅ Complete |
| `skills/definitions/*.yaml` | ✅ 6 skills defined |
| `utilities/module_loader.py` | ✅ Complete |
| `utilities/prompt_builder.py` | ✅ Complete |
| `utilities/session_initializer.py` | ✅ Complete |
| `utilities/resume_parser.py` | 🔴 Stub — not implemented |
| `services/sprite_generator.py` | ✅ Complete |
| `api/routes/session.py` | ✅ Complete |
| `api/routes/turn.py` | ✅ Complete |
| `api/routes/world.py` | ✅ Complete |
| `api/routes/modules.py` | ✅ Complete |
| `modules/posh/` | ✅ Scenarios complete |
| `modules/cybersecurity/` | ✅ Scenarios complete |
| `modules/ethics/` | ✅ Scenarios complete |
| `modules/escalation/` | ✅ Scenarios complete |
| `tools/` | 🔴 All stubs — not implemented |
| `frontend/src/` | 🔴 Mostly stubs |
| `frontend-contract/types.ts` | ✅ Complete |
| `frontend-contract/client.ts` | ✅ Complete |
| `scripts/play.py` | ✅ CLI test harness — functional |

---

## Workstreams

Each workstream owns a specific slice of the system and can build independently.

| Workstream | What to build | Where to build it |
|---|---|---|
| **Core** | `GameState` models, `SessionManager`, `Orchestrator` | `backend/core/` |
| **Agents** | Scenario, Actor, Evaluator, Coach, Guardrail agents | `backend/agents/` |
| **Skills** | Skill YAML definitions, `SkillRegistry` | `backend/skills/` |
| **Tools** | Individual tool functions | `backend/tools/` |
| **Utilities** | `ResumeParser`, `ModuleLoader`, `SessionInitializer`, `PromptBuilder` | `backend/utilities/` |
| **Content** | POSH, cybersecurity, ethics, escalation module YAML files | `backend/modules/` |
| **API** | FastAPI route implementations | `backend/api/` |
| **Arena UI** | Battle screen, HP bar, choice cards, actor panel | `frontend/src/renderer/screens/Arena/` + `components/` |
| **Setup UI** | Resume input and module selection screen | `frontend/src/renderer/screens/Setup/` |
| **Debrief UI** | Debrief screen and turn breakdown | `frontend/src/renderer/screens/Debrief/` |
| **Electron** | Main process, server manager, IPC | `frontend/src/main/` |

## Where to Start (by workstream)

### Core team
1. Everything in `core/` is implemented — review it before touching anything
2. `game_state.py` is the shared contract — changes require team discussion
3. Run `scripts/play.py` to see it working end-to-end

### Agents team
1. All 5 agents are implemented — read each file's docstring before touching it
2. `GuardrailAgent` validates player input and clamps agent outputs — run it first per turn
3. Actor agents maintain per-session `ChatSession` instances in the `Orchestrator`
4. Test with `scripts/play.py`

### Skills team
1. `skill_registry.py` and the 6 starter skill YAMLs in `definitions/` are implemented
2. Add more skills by dropping a new `.yaml` in `definitions/` — follow the existing schema
3. Skills are injected at session start by `PromptBuilder` — no per-turn loading

### Utilities team
1. `ModuleLoader`, `PromptBuilder`, and `SessionInitializer` are all implemented
2. `ResumeParser` is the one remaining stub — implement it
3. `PromptBuilder` is how skills get woven into actor prompts — read it before changing anything

### Content team
1. Four modules exist: `posh/`, `cybersecurity/`, `ethics/`, `escalation/`
2. Read an existing scenario YAML to understand the schema before authoring new ones
3. The full scenario schema is documented in `planning/COMPONENTS.md`
4. The `goal` field is the most important — Evaluator, Scenario Agent, and Coach all use it

### API team
1. All routes are implemented and functional
2. Test with `curl` or `scripts/play.py` before touching route code
3. `frontend-contract/client.ts` is the typed client — it mirrors the API contract exactly

### Arena / Setup / Debrief UI teams
1. Read `frontend/README.md` — key contracts are listed
2. Use `frontend-contract/client.ts` for all backend calls — never call the backend directly
3. All types are in `frontend-contract/types.ts` — import from there, not from `core/`
4. Build against the mock data below before the backend is connected

### Electron team
1. `server-manager.ts` is stubbed — implement process spawning and health check polling
2. In dev mode, assume backend is already running on `localhost:8000`
3. Handle app quit by calling `stopBackend()`

---

## Rules

### The Golden Rule
**`backend/core/game_state.py` is the shared contract.** Do not change it without a team discussion. Every agent, every API route, and every frontend store depends on it.

### Stubs
Every file has a stub with a docstring explaining:
- What this component does
- Its input/output contract
- What it depends on
- What depends on it

Read the stub before writing any code in that file.

### `TODO` comments
Stubs contain `TODO:` comments marking exactly what needs to be implemented.
Do not remove a `TODO` until the thing is actually implemented and tested.

### No cross-workstream imports (except Core)
- Agents import from `core/` and `tools/` — not from each other
- Utilities import from `core/` — not from agents
- API imports from `core/` and agents — not from utilities directly
- Frontend only talks to the backend via HTTP — never imports Python
- Frontend only calls the backend via `frontend-contract/client.ts`

### Branching
- Work in feature branches: `feat/<workstream>/<what-you-built>`
- Example: `feat/agents/evaluator-agent`
- Open a PR when your component passes a basic smoke test

---

## Mock Data (for frontend development)

Use this to build the Arena UI before the backend is connected:

```typescript
const mockGameState = {
  session_id: "mock-001",
  player_profile: {
    name: "Alex",
    role: "Software Engineer",
    seniority: "Mid-level",
    domain: "Technology",
    raw_context: "",
  },
  player_hp: 65,
  max_hp: 100,
  current_step: 3,
  max_steps: 6,
  status: "active",
  module_id: "posh",
  scenario_id: "posh_bystander_001",
  actors: [
    {
      actor_id: "marcus",
      persona: "Dismissive senior colleague",
      role: "The offender",
      personality: "Confident, deflects with humour",
      skills: ["social_pressure", "deflection"],
      tools: [],
      memory: [],
      current_directive: "Apply pressure",
    },
    {
      actor_id: "claire",
      persona: "Newer team member",
      role: "The target",
      personality: "Reserved, doesn't want to cause a scene",
      skills: ["hesitation"],
      tools: [],
      memory: [],
      current_directive: "Stay quiet unless engaged",
    },
  ],
  history: [
    {
      step: 3,
      situation:
        "Marcus leans over to Claire and says something quietly. She shifts in her seat " +
        "and looks uncomfortable. He notices you watching and smirks.",
      turn_order: ["marcus"],
      directives: { marcus: "Double down" },
      actor_reactions: [
        { actor_id: "marcus", dialogue: "Relax, it's just a joke. Everyone's so sensitive these days." },
      ],
      choices_offered: [
        { label: "Ask Claire privately if she's okay after lunch", valence: "positive" },
        { label: "Laugh it off and look away", valence: "negative" },
        { label: "Change the subject loudly to break the tension", valence: "neutral" },
      ],
      player_choice: "",
      evaluation: null,
      hp_delta: 0,
      narrative_branch: "escalation",
    },
  ],
};
```

---

## Planning Docs

All design decisions, open questions, and architecture are in `planning/`.
Before making a significant design decision, check `planning/OPEN_QUESTIONS.md` —
it may already be answered. If you make a decision, log it in `planning/DISCUSSIONS.md`.
