# Architecture — Your Cubicle Ally

> Hackathon 2026 · Technical Reference

---

## What It Is

**Your Cubicle Ally** is a Pokémon PvP-style compliance training game. Employees fight through real workplace scenarios — choosing actions, taking HP damage for bad calls, and receiving a full AI-generated debrief at the end. It runs as a local desktop app with Google Gemini powering every intelligent piece of the system.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Electron Shell                     │
│  ┌──────────────────┐    ┌────────────────────────┐ │
│  │  React Frontend  │◄──►│  server-manager.ts     │ │
│  │  (TypeScript)    │    │  (spawns backend child) │ │
│  └──────────┬───────┘    └────────────────────────┘ │
└─────────────┼───────────────────────────────────────┘
              │ HTTP (localhost:8000)
┌─────────────▼───────────────────────────────────────┐
│               FastAPI Backend (Python)              │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │                 Orchestrator                 │   │
│  │  Guardrail → Evaluator → Scenario → Actors   │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ SQLite   │  │  YAML    │  │   Google Gemini   │  │
│  │ Sessions │  │ Scenarios│  │   (all AI calls)  │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop shell | Electron 28 |
| Frontend | React + TypeScript |
| State management | Zustand |
| Backend API | FastAPI (Python) |
| Data validation | Pydantic v2 |
| Config format | YAML (scenarios + skills) |
| Database | SQLite (stdlib `sqlite3`) |
| AI SDK | `google-genai` (Gemini) |
| TUI test harness | Textual (Python) |
| Type contract | Shared TypeScript types (`frontend-contract/`) |

No external agentic framework (LangChain, LangGraph, AutoGen, etc.) is used. The orchestration layer is custom-built.

---

## Repository Layout

```
your-cubicle-ally/
├── backend/              # Python/FastAPI — agents, game engine, API
├── frontend/             # Electron + React (TypeScript) — game UI
├── frontend-contract/    # Shared TypeScript types + typed API client
├── scripts/              # CLI test harness (play.py, Textual TUI)
├── docs/                 # PITCH.md, ARCHITECTURE.md
├── planning/             # Design notes and open questions
├── main.js               # Electron main process entry
├── preload.js            # Electron preload bridge
└── renderer/             # Legacy HTML/JS renderer (dev fallback)
```

---

## Backend Structure

```
backend/
├── api/
│   ├── main.py           # FastAPI app, lifespan, router registration
│   ├── deps.py           # Dependency injection helpers
│   └── routes/
│       ├── session.py    # Session lifecycle endpoints
│       ├── turn.py       # Turn submission endpoint
│       ├── modules.py    # Module/scenario listing
│       ├── world.py      # Gemini image generation endpoint
│       └── tts.py        # Gemini TTS endpoints
│
├── agents/               # All Gemini-powered agents (see AI section)
│   ├── actor_agent.py
│   ├── coach_agent.py
│   ├── evaluator_agent.py
│   ├── guardrail_agent.py
│   └── scenario_agent.py
│
├── core/
│   ├── game_state.py     # All Pydantic models
│   ├── orchestrator.py   # Turn pipeline coordinator
│   └── session_manager.py # SQLite persistence + in-memory cache
│
├── modules/              # YAML scenario files (12 scenarios, 4 modules)
├── services/
│   ├── sprite_generator.py  # Gemini image gen
│   └── tts_service.py       # Gemini TTS
│
├── skills/
│   ├── skill_registry.py    # Loads + caches skill YAMLs at startup
│   └── definitions/         # 6 skill YAML files
│
└── utilities/
    ├── prompt_builder.py    # Assembles all agent system prompts
    ├── module_loader.py     # Loads + validates scenario YAMLs
    └── session_initializer.py # Builds GameState from YAML at session start
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/session/start` | Create a new game session |
| `GET` | `/session/{id}` | Get current GameState |
| `POST` | `/session/{id}/retry` | Reset to same scenario at full HP |
| `GET` | `/session/{id}/debrief` | Run CoachAgent → full structured debrief |
| `POST` | `/turn/submit` | Submit player choice → run full turn pipeline |
| `GET` | `/modules` | List all modules + scenarios |
| `GET` | `/modules/{id}` | List scenarios for a specific module |
| `POST` | `/world/generate` | Generate environment image + actor sprites |
| `POST` | `/tts/speech` | Generate WAV audio for actor dialogue |
| `POST` | `/tts/speech/base64` | Same but returns base64 data URL |

---

## Turn Pipeline

Every player action flows through the **Orchestrator** in this fixed sequence:

```
Player Choice
      │
      ▼
┌─────────────┐
│  Guardrail  │  Validate input (rule-based + LLM safety check for free-write)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Evaluator  │  Score choice 0–100 → HP delta + reasoning
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  PlayerDrift     │  Compute rolling performance (consecutive bad turns,
│  (Orchestrator)  │  avg score, HP trend) → inject corrective guidance
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│  Scenario   │  Advance narrative, determine turn order,
│  Agent      │  generate 3 choices, check early resolution
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Guardrail  │  Clamp any out-of-bounds agent outputs
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Actor      │  Each actor in turn order generates in-character
│  Agents (N) │  dialogue (persistent Gemini Chat memory)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Session    │  Persist updated GameState to SQLite
│  Manager    │
└─────────────┘
       │
       ▼
  Updated GameState → Frontend
```

---

## Data Persistence

**SQLite** (single file: `backend/sessions.db`)

```sql
CREATE TABLE sessions (
    session_id  TEXT PRIMARY KEY,
    game_state  TEXT NOT NULL,   -- full GameState serialized as JSON
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

The full `GameState` Pydantic model is serialized with `model_dump_json()`. An in-memory dict (`_cache`) acts as a read-through layer to avoid repeated SQLite reads on every turn.

---

## Scenario + Skill System

### Scenario YAML

All compliance content is defined in YAML. Adding a new scenario = dropping a file in `modules/<domain>/scenarios/`. Zero engine changes.

```yaml
id: posh_bystander_001
module_id: posh
title: "The Uncomfortable Joke"
max_steps: 10
starting_hp: 100
allow_early_resolution: true

scoring:
  great: {min: 5,   max: 15}   # score >= 80
  good:  {min: -5,  max: 0}    # score 50–79
  poor:  {min: -15, max: -5}   # score 20–49
  bad:   {min: -25, max: -15}  # score < 20

rubric:
  goal: "..."
  key_concepts: [...]
  few_shot_examples: [{choice, score, reasoning}, ...]

entry_turn:
  situation: "..."
  turn_order: [marcus, claire]
  directives: {marcus: "...", claire: "..."}
  choices_offered: [{label, valence}, ...]

actors:
  - actor_id: marcus
    persona: "..."
    role: "..."
    personality: "..."
    skills: [social_pressure, deflection]
```

**12 live scenarios across 4 modules:**

| Module | Scenarios |
|---|---|
| POSH | The Uncomfortable Joke, Microaggression in Stand-ups, Customer Crossing the Line, Team Offsite |
| Cybersecurity | USB in the Lobby, Password Reuse Boss, WiFi Trap |
| Ethics | Favor for a Friend, Data for Discount, Side Gig Conflict |
| Escalation | Informal Complaint, Retaliation Risk, Low Performer vs. Bias |

### Skill YAML

Skills are composable behavioral bundles injected as text fragments into actor system prompts. Each skill has a `prompt_injection`, `grants_tools` list, and `conflicts_with` list.

**6 skills:** `authority`, `bystander_effect`, `deflection`, `empathy`, `hesitation`, `social_pressure`

Example: Marcus's `social_pressure` + `deflection` combination is a designed game mechanic — he invokes group norms to deflect accountability. Both behaviors are built from reusable skill primitives, not hardcoded logic.

---

## Frontend Structure

```
frontend/src/
├── main/
│   ├── index.ts           # Electron main process
│   ├── preload.ts         # Electron preload bridge
│   └── server-manager.ts  # Spawns FastAPI backend as child process
└── renderer/
    ├── App.tsx            # Root component, screen routing
    ├── store/
    │   ├── gameStore.ts   # Game state (Zustand)
    │   └── sessionStore.ts
    ├── screens/
    │   ├── Setup/         # Profile input + module selector
    │   ├── Arena/         # Battle screen + turn handler
    │   └── Debrief/       # Coach debrief display
    └── components/
        ├── ActorPanel/    # Character display cards
        ├── ChoiceCards/   # A/B/C choice + free-write input
        ├── HPBar/         # Animated HP bar
        └── SituationPanel/
```

**`frontend-contract/`** contains shared TypeScript types that mirror the backend Pydantic models exactly, providing a typed API contract between frontend and backend.

---

## CLI Test Harness (`scripts/play.py`)

A full **Textual TUI** (terminal UI) that drives the backend over HTTP — used for development and demo without needing the Electron frontend:

- Two tabs: **Game** (arena + choices) and **Logs** (raw API event stream)
- 5-step player setup flow (name, role, seniority, domain, resume)
- Dynamic scenario picker from `/modules`
- ASCII character sprites, HP bar, step counter, dialogue chat log
- A/B/C/F choice input (F = free-write)
- Full debrief view with per-turn breakdown
- Retry flow, guardrail rejection handling

---

---

## Google AI / Gemini — Every Usage

This is the complete map of how Google Gemini is used across the system.

---

### 1. Actor Agents — Persistent Chat Memory

**File:** `backend/agents/actor_agent.py`  
**SDK call:** `client.aio.chats.create(model=..., config={"system_instruction": ...})`

Each actor (e.g., Marcus, Claire) is backed by a **persistent Gemini `Chat` object** that lives for the entire session. The actor's persona, role, personality, and skills are locked into the `system_instruction` at session start. Every subsequent turn sends only a short dynamic message — the current situation + a directive from the Scenario Agent.

**Why this matters:** Marcus *remembers* that you called him out two turns ago. He doesn't reset. This is genuine cross-turn character memory with zero external memory store — Gemini manages the conversation history natively.

---

### 2. Evaluator Agent — JSON Mode Scoring

**File:** `backend/agents/evaluator_agent.py`  
**SDK call:** `client.aio.models.generate_content(...)` with `response_mime_type="application/json"`

Scores the player's choice 0–100 against a scenario-specific rubric grounded in few-shot examples from the YAML. Returns structured JSON:

```json
{
  "score": 72,
  "hp_delta": -3,
  "reasoning": "...",
  "is_critical_failure": false
}
```

Gradient scoring — a free-write response that is partially correct gets partial credit. Not binary pass/fail. The rubric and few-shot examples are injected into the prompt by `PromptBuilder`.

---

### 3. Scenario Agent — Narrative Game Master

**File:** `backend/agents/scenario_agent.py`  
**SDK call:** `client.aio.models.generate_content(...)` with JSON mode

The game master. Every turn it determines:
- Which actors speak this turn (`turn_order`)
- What directive each actor receives
- What the situation summary is for the player
- What three choices to offer
- Whether early resolution is possible

The Orchestrator enriches the Scenario Agent's prompt with a **narrative arc phase** (`OPENING / MID / ESCALATION / CLOSING / FINAL`) derived from the current step percentage, giving the narrative genuine dramatic structure without scripted branches.

---

### 4. Coach Agent — End-of-Game Debrief

**File:** `backend/agents/coach_agent.py`  
**SDK call:** `client.aio.models.generate_content(...)` with JSON mode

Runs once after the final turn. Receives the full game history (every turn, choice, score, HP delta, and actor dialogue). Returns a structured debrief:

- Overall performance summary
- Per-turn breakdown: what the player did, what score they received, and *why* — referencing the specific compliance concept
- Recommended study areas

This is the primary learning artifact of the game.

---

### 5. Guardrail Agent — Safety + Output Clamping

**File:** `backend/agents/guardrail_agent.py`  
**SDK call:** `client.aio.models.generate_content(...)` with JSON mode (only for free-write input)

Three-layer protection:

1. **Rule-based checks** (no LLM): empty input, length limits, structural validation
2. **LLM safety check** (Gemini): for free-write player input only — catches prompt injection, off-topic content, abuse
3. **Output clamping**: validates Scenario Agent and Evaluator outputs are within expected bounds (e.g., HP delta in range) before they reach the game engine

---

### 6. Sprite & Environment Generation — Gemini Image Generation

**File:** `backend/services/sprite_generator.py`  
**SDK call:** `client.aio.models.generate_content(...)` with `response_modalities=["TEXT", "IMAGE"]`  
**Model:** `gemini-2.0-flash-exp-image-generation`

Generates all visual assets:

- **Environment frames** — 2 frames per scenario for a crossfade background animation
- **Actor sprites** — 4-frame idle animation loops per actor character

Assets are generated once and cached (in-memory → disk at `backend/cache/sprite_cache/`). The same scenario reuses cached assets across sessions.

---

### 7. Text-to-Speech — Gemini Native TTS

**File:** `backend/services/tts_service.py`  
**SDK call:** `client.aio.models.generate_content(...)` with `response_modalities=["AUDIO"]` and `SpeechConfig`  
**Model:** `gemini-2.5-flash-preview-tts`

Generates voice audio for actor dialogue. Voice gender is selected by:

1. Name lookup table (known names → gender)
2. Persona keyword parsing (e.g., "he/him" in the persona field)
3. Heuristic name-ending patterns as fallback

Raw PCM from Gemini is wrapped in a WAV header before being returned. Available as raw WAV (`/tts/speech`) or base64 data URL (`/tts/speech/base64`).

---

### Summary of Gemini Usage

| Usage | Agent/Service | SDK Pattern | Model |
|---|---|---|---|
| Actor dialogue + memory | `ActorAgent` | Persistent `Chat` | `gemini-2.0-flash` |
| Player choice scoring | `EvaluatorAgent` | `generate_content` + JSON mode | `gemini-2.0-flash` |
| Narrative + choices | `ScenarioAgent` | `generate_content` + JSON mode | `gemini-2.0-flash` |
| End-of-game debrief | `CoachAgent` | `generate_content` + JSON mode | `gemini-2.0-flash` |
| Input/output safety | `GuardrailAgent` | `generate_content` + JSON mode | `gemini-2.0-flash` |
| Visual asset generation | `SpriteGenerator` | `generate_content` + IMAGE modality | `gemini-2.0-flash-exp-image-generation` |
| Actor voice synthesis | `TTSService` | `generate_content` + AUDIO modality | `gemini-2.5-flash-preview-tts` |

All models are configurable via environment variables (`GEMINI_MODEL`, `GEMINI_IMAGE_MODEL`, `GEMINI_TTS_MODEL`) in `backend/.env`.

---

## Key Design Decisions

**No external agentic framework.** The Orchestrator, turn pipeline, and player drift system are all custom Python. This keeps the dependency surface minimal and the control flow explicit and debuggable.

**Actor memory via Chat, not a vector DB.** Gemini's `Chat` API manages conversation history natively. Each actor's `Chat` object persists in the Orchestrator's in-memory dict for the life of the session. This gives genuine cross-turn character continuity without adding a memory store dependency.

**Content in YAML, engine in Python.** Scenario authors write YAML. They never touch the engine. The `ModuleLoader` picks up new scenario files at startup. This makes the system white-label ready — HR teams can author their own compliance modules without any code changes.

**Skills as composable text injections.** An actor's behavior is assembled from named skill primitives at prompt-build time. Marcus's `social_pressure + deflection` combination is a designed game mechanic — both behaviors are reusable across any actor in any scenario.

**Gradient scoring, not binary pass/fail.** The Evaluator scores responses 0–100. A partially correct free-write answer still gets partial credit. Choice valence (`great/good/poor/bad`) is not shown to the player — the game is harder than it looks.

**HP drains only.** Good choices preserve HP; only bad choices drain it. This design creates genuine stakes without making the game feel arbitrary.
