# Open Questions, Gaps & Things to Think About

This is a living document. Add anything here that's unresolved — design decisions, technical unknowns, UX gaps, edge cases. Tag each with a status.

**Statuses:** `🔴 Unresolved` | `🟡 Leaning toward X` | `🟢 Decided` (link to DISCUSSIONS.md entry)

---

## Product / Design

| # | Question | Status | Notes |
|---|---|---|---|
| P1 | Do we want a "win" state, or does the scenario always run to completion? | 🟢 Decided | Win = complete all steps with HP > 0 → debrief. Lose = HP hits 0 → retry or debrief. |
| P2 | What happens when a player "loses" (HP hits 0)? Restart same scenario? Jump to debrief? | 🟢 Decided | Show loss screen with two options: retry same scenario, or go straight to debrief. |
| P3 | Should correct answers recover HP, or only incorrect ones drain it? | 🟢 Decided | Drain only. No recovery. Keeps it simple for MVP. |
| P4 | How do we prevent players from just spamming the free-write option with nonsense? | 🟢 Decided | Evaluator handles it naturally — gibberish scores 0 and takes max HP damage. No separate gate for MVP. |
| P5 | Does the player see any hint about which choice is "better" before selecting? | 🟢 Decided | No hints. Valence is hidden from the player entirely. |
| P6 | Should the 3 choices always include one clearly bad, one nuanced, one clearly good? Or all ambiguous? | 🟢 Decided | Valence shifts by stage — early turns more ambiguous, later turns clearer stakes. Keep it simple: the Choices Agent just receives the current step number and adjusts accordingly. |
| P7 | How many steps per scenario? Fixed or variable? | 🟡 Leaning toward 5–8 | Needs playtesting |
| P8 | Do we show HP damage amount after each turn, or just animate the bar? | 🟢 Decided | Animate bar decrease + show current / max (e.g. 65 / 100). No floating damage number. |
| P9 | Is there a time limit per turn, or open-ended? | 🟢 Decided | No timer. Self-paced — the system is a learning tool, not a stress test. |
| P10 | How do we handle very sensitive POSH scenarios — what's the tone/guardrail approach? | 🟢 Decided | Realistic but restrained — discomfort comes from the dynamic, not graphic language. See FUTURES.md for configurable intensity extension. |

---

## Agent / LLM Design

| # | Question | Status | Notes |
|---|---|---|---|
| A1 | One LLM with different system prompts, or separate model calls per agent role? | 🟡 Leaning toward separate calls | More control, easier debugging, cleaner skill injection |
| A2 | How deterministic should the Choices Agent be? Should choices repeat across playthroughs? | 🟢 Decided | Deterministic intent (pos/neutral/neg valence fixed per step), randomized wording each run. Consistent learning outcome, variable feel. |
| A3 | How do we prevent the Evaluator Agent from being too lenient or too harsh? | 🟢 Decided | Rubric + few-shot examples + structured JSON output (score, hp_delta, reasoning, is_critical_failure). Each scenario also carries setup, actor roles/personalities, and a scenario goal — all fed to the Evaluator as context. |
| A4 | How does the Scenario Agent broadcast state to Actor Agents — one call each, or batched? | 🟢 Decided | Scenario Agent determines turn order first; dispatches to actors per that order (sequential or parallel depending on the turn) |
| A5 | How do we handle free-write responses that are partially correct? | 🟢 Decided | Gradient scoring — Evaluator scores 0–100 continuously; hp_delta scales proportionally. No binary pass/fail. |
| A6 | Do agents share a single context window or do we manually construct history each turn? | 🟢 Decided | Two-layer context: (1) Shared context — scenario goal, setup, actor roster, player profile, full turn history. (2) Per-actor history — each actor's own dialogue memory. Actors use both. Scenario Agent and Evaluator use shared context only. |
| A7 | How do we ground the Evaluator Agent in actual compliance law/policy? | 🟢 Decided | Static rubrics defined in the module YAML + shared context. No RAG for MVP. Rubric quality is the calibration lever. |
| A8 | Which LLM provider? OpenAI vs Anthropic vs open-source? | 🟢 Decided | Google Gemini Flash via google-generativeai SDK. |
| A9 | How many Actor Agents max per scenario before latency becomes unacceptable? | 🟢 Decided | Max 3. Hard cap. |
| A10 | Can Actor Agents have conflicting skills? How do we detect/prevent invalid skill combos? | 🟢 Decided | Validated at module load time in SkillRegistry. Conflicting skills log a warning and the lower-priority skill is dropped. No runtime enforcement. |
| A11 | Do Actor Agents "remember" across turns, or are they stateless each turn? | 🟢 Decided | Actors have per-actor memory (Gemini ChatSession). Shared context covers the full game; actor memory covers their own dialogue history. |
| A12 | Should the Scenario Agent see individual actor dialogue, or just react to the player? | 🟢 Decided | Scenario Agent works from shared context (which includes actor reactions from each turn). It sees everything. |

---

## Technical / Engineering

| # | Question | Status | Notes |
|---|---|---|---|
| T1 | How is session state persisted — in-memory, Redis, DB? | 🟡 Leaning toward in-memory + SQLite | SQLite fits Electron's local-first model; no Redis needed |
| T2 | Is the backend stateful (WebSocket) or stateless (REST per turn)? | 🟡 Leaning toward REST + IPC | Electron IPC handles real-time feel; REST for backend simplicity |
| T3 | How are modules defined and stored? YAML files? DB records? | 🟢 Decided: YAML files | See DISCUSSIONS.md [2026-02-28] |
| T4 | How is the resume/JD parsed? LLM extraction, or structured form? | 🟡 Leaning toward LLM extraction | Better UX; ResumeParser utility handles this |
| T5 | Do we need auth/user accounts for the hackathon MVP? | 🟡 Leaning toward no auth for MVP | Anonymous sessions; local SQLite per install |
| T6 | How do we handle LLM latency mid-turn without breaking the game feel? | 🟢 Decided | Actor portrait pulses / battle-style "thinking" animation while agents process. Actor dialogue streams character-by-character on arrival (Gemini streaming). |
| T7 | Should agent calls be parallelized per turn? | 🟢 Decided: Yes, partially | Evaluator first → then Scenario Agent + Actor Agents in parallel |
| T8 | How does the Electron main process communicate with the FastAPI backend? | 🟢 Decided | Main process spawns FastAPI as child process; renderer calls localhost HTTP |
| T9 | How do we bundle Python (FastAPI) inside an Electron app for distribution? | 🟡 Leaning toward PyInstaller | Bundle frozen Python binary with Electron; significant but solvable packaging work |
| T10 | Should skills be loaded dynamically at runtime or compiled into the agent at session start? | 🟢 Decided | Compiled at session start. Skills baked into actor prompt via PromptBuilder during SessionInitializer. Keeps per-turn processing fast and deterministic. |
| T11 | How do we validate module YAML files — schema validation at load time? | 🟢 Decided | Pydantic validation in ModuleLoader at startup. Invalid modules are excluded from registry with a logged warning — app does not crash. |

---

## Scope / MVP

| # | Question | Status | Notes |
|---|---|---|---|
| M1 | Which compliance module do we build first for the hackathon demo? | 🟢 Decided | POSH first. Module + scenario selection is managed by the frontend — player chooses both. |
| M2 | How many scenarios per module for the MVP? | 🟢 Decided | 1 scenario per module to start. Architecture must support fetching more — scenarios are addable without core changes. |
| M3 | Do we need a real user setup flow (resume upload) for MVP, or can we hardcode a persona? | 🟢 Decided | Resume upload supported. If parsing fails or result is too ambiguous, fall back to a default persona (e.g. "Mid-level professional, general industry"). |
| M4 | Do we need a debrief for MVP or can we show a simple score screen? | 🟢 Decided | Full debrief. It's the payoff of the whole session. |

---

## Skills System

| # | Question | Status | Notes |
|---|---|---|---|
| S1 | How are skills injected into an actor's prompt — appended, prepended, or woven in? | 🟢 Decided | Appended after persona + role blocks, each skill clearly delimited. Simple and debuggable. Handled by PromptBuilder at session start. |
| S2 | Can a player "break" an actor's skill through their choices? (e.g., persistence breaks Deflection) | 🟢 Decided | No for MVP. Skills fixed for the session. See FUTURES.md (F5). |
| S3 | Should skills be visible to the player (like Pokémon move lists) or hidden? | 🟢 Decided | Hidden. Realism over game-like UI for MVP. See FUTURES.md (F4). |
| S4 | Do skills evolve during a scenario, or are they fixed at session start? | 🟢 Decided | Fixed at session start. No evolution for MVP. See FUTURES.md (F5). |
| S5 | Who authors new skills — developers only, or can HR/content teams author YAML skills too? | 🟢 Decided | Developers only for MVP. Schema is clean enough for HR authoring in future. |

---

## Things to Think About — Parked for MVP

These are acknowledged but not blocking. Most are covered by existing decisions or deferred to FUTURES.md.

| Item | Resolution |
|---|---|
| Pokémon feel | Streaming actor dialogue + HP bar animation covers this for MVP. Avatars and music in Futures. |
| Observer scenarios | Already supported — actor model handles bystander roles natively. |
| Gaming the system | Gradient scoring makes it harder to game. Not a MVP concern. |
| Free-write UX | Pulsing actor portrait during Evaluator processing covers this. |
| Debrief turn references | Coach Agent gets full turn history including player choices — it can and should reference specific steps. |
| Actor-to-actor interaction | Supported via turn order — Scenario Agent can sequence actors to react to each other. Full support in Futures (F15). |
| Accessibility | Deferred to post-MVP. |
| Localization | Module YAML can declare `jurisdiction` field. Deferred to post-MVP (F3). |
