# Backend

Python / FastAPI backend. Runs as a local server spawned by the Electron main process.

## Stack
- **FastAPI** — API framework
- **Pydantic** — data models and validation
- **PyYAML** — module and skill definition loading
- **google-genai** — Gemini SDK for all LLM and image generation calls

## Structure

```
backend/
├── agents/          # Five agents: Scenario, Actor, Evaluator, Coach, Guardrail
├── skills/          # Skill system — base model, registry, and YAML definitions
├── tools/           # Callable tools available to agents (stubs)
├── modules/         # Compliance training modules — POSH, cybersecurity, ethics, escalation (YAML)
├── core/            # GameState models, SessionManager, Orchestrator
├── utilities/       # ResumeParser, ModuleLoader, SessionInitializer, PromptBuilder
├── services/        # Sprite and environment image generation (Gemini image gen)
├── api/             # FastAPI routes and app entry
└── cache/           # Sprite image cache (auto-created)
```

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# create a .env file with the following:
# GOOGLE_API_KEY=<your key>
# GEMINI_MODEL=gemini-2.0-flash        (or another Gemini text model)
# GEMINI_IMAGE_MODEL=gemini-2.0-flash-exp-image-generation
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
| `utilities/` | Utilities team | `ResumeParser`, `ModuleLoader`, `PromptBuilder`, `SessionInitializer` |
| `services/` | Utilities team | `SpriteGenerator` |
| `api/` | API team | REST contract (see route docstrings) |

## Key Contracts

- **Do not change** `core/game_state.py` models without a team discussion — everything depends on them
- **Agent outputs** must match the contract in each agent's module docstring
- **Module YAML** must conform to the schema in `planning/COMPONENTS.md`
- **Skill YAML** must conform to `skills/base_skill.py`
