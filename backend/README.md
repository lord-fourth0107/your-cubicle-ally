# Backend

Python / FastAPI backend. Runs as a local server spawned by the Electron main process.

## Stack
- **FastAPI** — API framework
- **Pydantic** — data models and validation
- **PyYAML** — module and skill definition loading
- **OpenAI / Anthropic** — LLM calls for all agents

## Structure

```
backend/
├── agents/          # The four agents (Scenario, Actor, Evaluator, Coach)
├── skills/          # Skill system — base model, registry, and YAML definitions
├── tools/           # Callable tools available to agents
├── modules/         # Compliance training modules (YAML)
├── core/            # Game state models, session manager, orchestrator
├── utilities/       # Resume parser, module loader, session init, prompt builder
├── api/             # FastAPI routes
└── tests/           # Tests
```

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your API keys (GOOGLE_API_KEY for AI-generated character sprites)
uvicorn api.main:app --reload --port 8000
```

## Ownership Map

| Folder | Owner | Key interfaces |
|---|---|---|
| `core/` | Core team | `GameState`, `SessionManager`, `Orchestrator` |
| `agents/` | Agents team | Each agent's `async` method signature |
| `skills/` | Skills team | `Skill` model, `SkillRegistry` |
| `tools/` | Tools team | Individual tool functions |
| `modules/` | Content team | YAML schema (see `planning/COMPONENTS.md`) |
| `utilities/` | Utilities team | `ResumeParser`, `ModuleLoader`, `PromptBuilder` |
| `api/` | API team | REST contract (see route docstrings) |

## Key Contracts

- **Do not change** `core/game_state.py` models without a team discussion — everything depends on them
- **Agent outputs** must match the contract in each agent's module docstring
- **Module YAML** must conform to the schema in `planning/COMPONENTS.md`
- **Skill YAML** must conform to `skills/base_skill.py`
