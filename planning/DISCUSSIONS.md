# Discussions & Decision Log

A running log of key discussions, decisions made, and the reasoning behind them.
Add entries in reverse-chronological order (newest at the top).

---

## [2026-02-28] — Backend Implementation Complete

**Topic:** End-of-hackathon implementation status

**What's built:**
- `core/game_state.py` — full Pydantic model definitions for `GameState`, `Turn`, `ActorInstance`, `ScoringConfig`, `Choice`, `Evaluation`
- `core/session_manager.py` — SQLite persistence with in-memory cache for hot sessions; `create`, `get`, `apply_turn`, `reset`, `delete`
- `core/orchestrator.py` — full turn processing pipeline: GuardrailAgent → EvaluatorAgent → ScenarioAgent → ActorAgents (sequential per turn_order); maintains persistent `ActorAgent` instances per session
- `agents/scenario_agent.py` — Gemini JSON mode; determines turn order, sets per-actor directives, generates situation summary and next 3 choices
- `agents/actor_agent.py` — Gemini `ChatSession` per actor per session; static system prompt built once at session start; responds in character every turn
- `agents/evaluator_agent.py` — scores player choice 0–100 against rubric + few-shot examples; returns `hp_delta`, `reasoning`, `is_critical_failure`
- `agents/coach_agent.py` — runs once post-session; produces structured debrief with `outcome`, `overall_score`, `summary`, `turn_breakdowns[]`, `key_concepts[]`, `recommended_followup[]`
- `agents/guardrail_agent.py` — validates player input; clamps out-of-bounds agent outputs; raises `GuardrailViolation`
- `utilities/prompt_builder.py` — assembles all agent prompts; handles skill injection (appended after personality, clearly delimited); arc phase guidance (OPENING/MID/ESCALATION/CLOSING/FINAL)
- `utilities/module_loader.py` — loads and validates scenario YAML; cached after first load
- `utilities/session_initializer.py` — creates fresh `GameState` from scenario + player profile; pre-populates entry turn (step 0)
- `services/sprite_generator.py` — Gemini 2.0 Flash image generation; caches to `backend/cache/sprite_cache/`
- `api/` — all routes implemented: `/session/start`, `/session/{id}`, `/session/{id}/retry`, `/session/{id}/debrief`, `/turn/submit`, `/world/generate`, `/modules`, `/modules/{id}`
- `modules/` — 13 scenarios across 4 modules: POSH, cybersecurity, ethics, escalation
- `skills/definitions/` — 6 skill YAMLs: `social_pressure`, `deflection`, `hesitation`, `authority`, `empathy`, `bystander_effect`
- `frontend-contract/types.ts` — TypeScript types mirroring all Pydantic models
- `frontend-contract/client.ts` — typed API client for all endpoints
- `scripts/play.py` — full CLI test harness with Rich terminal UI; functional end-to-end

**Still outstanding:**
- `utilities/resume_parser.py` — stub only; fallback to default persona is in place
- `tools/` — all stubs; tools are not yet callable by agents
- `frontend/src/` — screens and components are stubs; `server-manager.ts` is stubbed

**Status:** Backend is demo-ready. Frontend UI is the remaining build.

---

## [2026-02-28] — All Open Questions Resolved

**Topic:** Final resolution sweep across all remaining questions

**Decisions:**
- **MVP module:** POSH. Frontend manages module + scenario selection. 1 scenario per module to start; architecture supports fetching more.
- **Resume upload:** Supported. Falls back to default persona ("Mid-level professional, general industry") if parsing is too ambiguous.
- **Debrief:** Full Coach Agent debrief — not a score screen.
- **Latency UX:** Actor portrait pulses while agents process. Actor dialogue streams character-by-character via Gemini streaming.
- **Skill loading:** Baked into actor prompt at session start by PromptBuilder. No per-turn loading.
- **Module validation:** Pydantic in ModuleLoader at startup. Invalid modules excluded with warning, app continues.
- **Skill injection:** Appended after persona + role blocks in actor prompt, each delimited. Handled by PromptBuilder.
- **Skill evolution / visibility / breaking:** All deferred to Futures. Fixed, hidden for MVP.
- **Conflicting skills:** SkillRegistry validates at load time. Lower-priority skill dropped with warning.
- **"Things to think about":** All acknowledged and either covered by existing decisions or deferred to Futures.

**Status:** All open questions resolved. Ready to build.

---

## [2026-02-28] — Context Model, HP Rules & Agent Caps

**Topic:** Resolving agent context, HP mechanics, and max actors

**Decisions:**
- **HP:** Drain only. No recovery on good answers. Max -40 per turn. Gradient: hp_delta scales to score (0–100).
- **Player hints:** None. Valence is fully hidden.
- **Free-write scoring:** Gradient — continuous 0–100 score, no binary pass/fail.
- **Context model — two layers:**
  - *Shared context*: scenario goal, setup, actor roster, player profile, full turn history, module rubric. Read by Scenario Agent, Evaluator, Coach Agent, and Actors (as grounding).
  - *Per-actor history*: each actor's own dialogue across turns, maintained as a Gemini ChatSession. Read by that actor only.
- **Evaluator grounding:** Static rubrics from module YAML + shared context. No RAG for MVP.
- **Max actors:** 3 hard cap per scenario.
- **Scenario Agent:** Uses shared context (which includes actor reactions per turn) — sees everything.

---

## [2026-02-28] — Scenario Schema & Evaluator Design

**Topic:** Enriching the scenario definition and Evaluator calibration approach

**Discussion:**
- Each scenario needs to carry enough context for every agent to do its job well
- The Evaluator needs the scenario goal, setup, actor roles/personalities, and few-shot examples — not just the rubric
- The `goal` field is the shared north star: Evaluator judges against it, Scenario Agent steers toward it, Coach Agent measures achievement of it

**Decisions:**
- Scenario YAML now includes: `goal`, `setup`, per-actor `role` + `personality`, and `evaluation_examples` (few-shot)
- Evaluator outputs structured JSON: `score`, `hp_delta`, `reasoning`, `is_critical_failure`
- Each actor in a scenario has both a `persona_ref` (reusable base) and scenario-specific `role` + `personality` overrides

---

## [2026-02-28] — Win / Loss State

**Decisions:**
- **Win** — player completes all steps with HP > 0 → goes directly to debrief
- **Lose** — HP hits 0 (or critical failure) → loss screen with two options: retry the same scenario, or skip to debrief
- Debrief always available regardless of outcome — learning is never gated

---

## [2026-02-28] — LLM Provider & SDK

**Decisions:**
- **LLM:** Google Gemini Flash (`gemini-1.5-flash`)
- **SDK:** `google-generativeai` directly — no LlamaIndex
- `EvaluatorAgent`, `ScenarioAgent`, `CoachAgent` use `GenerativeModel` with `response_mime_type="application/json"` for structured output
- `ActorAgent` uses a `ChatSession` per actor instance — Gemini maintains the conversation history natively, giving each actor persistent memory across turns
- All LLM calls are `async` via `generate_content_async` / `send_message_async`

---

## [2026-02-28] — Tech Stack Confirmed

**Topic:** Finalizing the stack

**Decisions:**
- **Backend:** Python (FastAPI) — local server, agent orchestration, all LLM calls
- **Frontend:** Electron — desktop app with React renderer for the battle UI
- Communication: Electron main process spawns the FastAPI server as a child process; renderer talks to it via HTTP over localhost (or IPC bridge)

---

## [2026-02-28] — Component Breakdown & Multi-Actor Model

**Topic:** Expanding agent design + breaking system into 6 core component buckets

**Discussion:**
- Scenarios can have 1–3 Actor Agents (not just one opponent) — enables observer/bystander scenarios
- Every actor is a **mini agent** with its own persona, skills[], and tools[]
- The Scenario Agent is the orchestrator/game master — it broadcasts state to actors, collects their reactions, generates next situation + 3 options (positive/neutral/negative valence)
- The 3 choices should always be labeled by valence — positive, neutral, negative — player doesn't know which is which
- Game environment is an **Electron desktop app** (not a web app)
- Skills are reusable behavioral bundles injected into actor prompts by PromptBuilder
- Tools are callable functions agents can invoke (get_compliance_policy, trigger_escalation, etc.)
- Modules are YAML files — self-contained content packs

**Decisions:**
- 6 core component buckets: Agents / Skills / Tools / Modules / Utilities / Game Environment
- YAML for module definitions — version-controllable and authorable by non-devs
- SQLite for local state persistence (fits Electron local-first model)
- Evaluator runs first per turn; Scenario Agent + Actor Agents run in parallel after
- Actor Agents maintain per-actor conversation history (their own "perspective")

**Open Items:**
- How to bundle Python backend inside Electron (T9)
- Skill injection strategy in PromptBuilder (S1)
- Actor Agent parallelization approach (A4)
- Latency handling mid-turn (T6)

---

## [2026-02-28] — Core System Design

**Topic:** Defining the full concept and system architecture

**Discussion:**
- The system is a compliance training platform (POSH, Security, etc.)
- Core mechanic: Pokemon PvP-style battle interface
- User flow: Resume/JD upload → module selection → scenario battle → debrief
- Player has HP that is drained by bad answers; choices are presented as 3 options + free-write
- The scenario evolves based on choices — branching narrative, not fixed script
- System must be modular (new compliance modules = new plug-in), extendable, and clean

**Decisions:**
- Four distinct agents: Scenario Agent, Choices Agent, Evaluator Agent, Coach Agent
- GameState is the single source of truth for a session — tracks HP, turn history, current step
- Modules are self-contained definitions (scenarios, rubric, objectives) — drop in to add new topics
- Debrief is a first-class feature, not an afterthought

**Open Items:**
- See OPEN_QUESTIONS.md — many product and technical decisions still unresolved
- Priority: decide on MVP module (likely POSH), MVP scope, and whether to skip auth for hackathon

---

## [2026-02-28] — Initial Kickoff

**Topic:** Project scope and direction

**Discussion:**
- Project started for Hackathon 2026
- Core concept: interactive agentic training system for workplace scenarios
- Name: "Your Cubicle Ally"

**Decisions:**
- Start with planning/ideation phase before any code
- Use `planning/` directory for structured thinking

---

_Template for future entries:_

```
## [YYYY-MM-DD] — <Topic Title>

**Topic:** <Short description>

**Discussion:**
- Point 1
- Point 2

**Decisions:**
- Decision made and why

**Open Items:**
- Follow-up needed
```
