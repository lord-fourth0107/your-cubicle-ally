# Contributing

This project is built in parallel across multiple workstreams. Read this before writing any code.

## Workstreams

Each workstream owns a specific slice of the system and can build independently.

| Workstream | What to build | Where to build it |
|---|---|---|
| **Core** | `GameState` models, `SessionManager`, `Orchestrator` | `backend/core/` |
| **Agents** | Scenario, Actor, Evaluator, Coach agents (LLM calls) | `backend/agents/` |
| **Skills** | Skill YAML definitions, `SkillRegistry` | `backend/skills/` |
| **Tools** | Individual tool functions | `backend/tools/` |
| **Utilities** | `ResumeParser`, `ModuleLoader`, `SessionInitializer`, `PromptBuilder` | `backend/utilities/` |
| **Content** | POSH module YAML and scenario files | `backend/modules/` |
| **API** | FastAPI route implementations | `backend/api/` |
| **Arena UI** | Battle screen, HP bar, choice cards, actor panel | `frontend/src/renderer/screens/Arena/` + `components/` |
| **Setup UI** | Resume input and module selection screen | `frontend/src/renderer/screens/Setup/` |
| **Debrief UI** | Debrief screen and turn breakdown | `frontend/src/renderer/screens/Debrief/` |
| **Electron** | Main process, server manager, IPC | `frontend/src/main/` |

## Where to Start (by workstream)

### Core team
1. Read `planning/ARCHITECTURE.md` — understand `GameState` and the turn data flow
2. `game_state.py` is already written — validate it, don't change it without discussion
3. Implement `SessionManager` methods (stubs in `session_manager.py`)
4. Implement `Orchestrator.process_turn` (stubs in `orchestrator.py`)

### Agents team
1. Read `planning/COMPONENTS.md` — agent contracts are all there
2. Each agent file has a docstring with the exact input/output contract
3. Start with `EvaluatorAgent` — it's the simplest and most critical
4. Use `PromptBuilder` (from Utilities team) to assemble prompts — don't hardcode them
5. All agent methods are `async` — use `await` for LLM calls

### Skills team
1. `base_skill.py` and `skill_registry.py` are written — implement `load_all` and `validate_compatibility`
2. The 6 starter skill YAMLs are written — add more as needed
3. Coordinate with Utilities team on how skills are injected in `PromptBuilder`

### Utilities team
1. Start with `ModuleLoader` — other teams need modules loaded to test anything
2. Then `PromptBuilder` — Agents team is blocked on this
3. `ResumeParser` and `SessionInitializer` can follow

### Content team
1. Read the full scenario schema in `planning/COMPONENTS.md`
2. The POSH scenario stub is at `backend/modules/posh/scenarios/posh_bystander_001.yaml`
3. Fill it in using the schema — `goal`, `setup`, `actors[]`, `evaluation_examples`, `entry_situation`
4. Coordinate with Agents team to test that the Evaluator interprets it correctly

### API team
1. All routes are stubbed in `backend/api/routes/` — implement them
2. Do not add new routes without updating the contract in the route docstring
3. The frontend hits `http://localhost:8000` — test your routes with curl or Postman first

### Arena / Setup / Debrief UI teams
1. Read `frontend/README.md` — key contracts are listed
2. The backend API shape is in the route docstrings and `store/gameStore.ts`
3. Build against the mock data below before the backend is ready

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
  player_hp: 65,
  max_hp: 100,
  current_step: 3,
  max_steps: 6,
  status: "active",
  current_situation:
    "Raj leans over to Priya and says something quietly. She shifts in her seat " +
    "and looks uncomfortable. He notices you watching and smirks.",
  current_choices: [
    { label: "Ask Priya privately if she's okay after lunch", valence: "positive" },
    { label: "Laugh it off and look away", valence: "negative" },
    { label: "Change the subject loudly to break the tension", valence: "neutral" },
  ],
  current_actor_reactions: [
    { actor_id: "raj", dialogue: "Relax, it's just a joke. Everyone's so sensitive these days." },
  ],
};
```

---

## Planning Docs

All design decisions, open questions, and architecture are in `planning/`.
Before making a significant design decision, check `planning/OPEN_QUESTIONS.md` —
it may already be answered. If you make a decision, log it in `planning/DISCUSSIONS.md`.
