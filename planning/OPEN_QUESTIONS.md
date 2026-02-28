# Open Questions, Gaps & Things to Think About

This is a living document. Add anything here that's unresolved — design decisions, technical unknowns, UX gaps, edge cases. Tag each with a status.

**Statuses:** `🔴 Unresolved` | `🟡 Leaning toward X` | `🟢 Decided` (link to DISCUSSIONS.md entry)

---

## Product / Design

| # | Question | Status | Notes |
|---|---|---|---|
| P1 | Do we want a "win" state, or does the scenario always run to completion? | 🟢 Decided | Win = complete all steps with HP > 0 → debrief. Lose = HP hits 0 → retry or debrief. |
| P2 | What happens when a player "loses" (HP hits 0)? Restart same scenario? Jump to debrief? | 🟢 Decided | Show loss screen with two options: retry same scenario, or go straight to debrief. |
| P3 | Should correct answers recover HP, or only incorrect ones drain it? | 🟡 Leaning toward drain-only | Simpler, but recovery could reward excellence |
| P4 | How do we prevent players from just spamming the free-write option with nonsense? | 🟢 Decided | Evaluator handles it naturally — gibberish scores 0 and takes max HP damage. No separate gate for MVP. |
| P5 | Does the player see any hint about which choice is "better" before selecting? | 🔴 Unresolved | Probably not — that defeats the purpose |
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
| A5 | How do we handle free-write responses that are partially correct? | 🔴 Unresolved | Evaluator needs a gradient scoring approach |
| A6 | Do agents share a single context window or do we manually construct history each turn? | 🟡 Leaning toward manual construction | Per-actor history gives each actor their own "perspective" |
| A7 | How do we ground the Evaluator Agent in actual compliance law/policy? | 🔴 Unresolved | RAG over compliance documents? Fine-tuning? Static rubrics? |
| A8 | Which LLM provider? OpenAI vs Anthropic vs open-source? | 🟢 Decided | Google Gemini Flash. Agents built using LlamaIndex. |
| A9 | How many Actor Agents max per scenario before latency becomes unacceptable? | 🔴 Unresolved | 2–3 feels right; needs benchmarking |
| A10 | Can Actor Agents have conflicting skills? How do we detect/prevent invalid skill combos? | 🔴 Unresolved | COMPONENTS.md has `conflicts_with` field in skill schema — needs enforcement logic |
| A11 | Do Actor Agents "remember" across turns, or are they stateless each turn? | 🔴 Unresolved | Per-actor conversation history in ActorInstance suggests memory — but how long? |
| A12 | Should the Scenario Agent see individual actor dialogue, or just react to the player? | 🔴 Unresolved | Seeing actor reactions allows richer narrative weaving |

---

## Technical / Engineering

| # | Question | Status | Notes |
|---|---|---|---|
| T1 | How is session state persisted — in-memory, Redis, DB? | 🟡 Leaning toward in-memory + SQLite | SQLite fits Electron's local-first model; no Redis needed |
| T2 | Is the backend stateful (WebSocket) or stateless (REST per turn)? | 🟡 Leaning toward REST + IPC | Electron IPC handles real-time feel; REST for backend simplicity |
| T3 | How are modules defined and stored? YAML files? DB records? | 🟢 Decided: YAML files | See DISCUSSIONS.md [2026-02-28] |
| T4 | How is the resume/JD parsed? LLM extraction, or structured form? | 🟡 Leaning toward LLM extraction | Better UX; ResumeParser utility handles this |
| T5 | Do we need auth/user accounts for the hackathon MVP? | 🟡 Leaning toward no auth for MVP | Anonymous sessions; local SQLite per install |
| T6 | How do we handle LLM latency mid-turn without breaking the game feel? | 🔴 Unresolved | Streaming actor reactions? "Thinking..." battle animation? |
| T7 | Should agent calls be parallelized per turn? | 🟢 Decided: Yes, partially | Evaluator first → then Scenario Agent + Actor Agents in parallel |
| T8 | How does the Electron main process communicate with the FastAPI backend? | 🟢 Decided | Main process spawns FastAPI as child process; renderer calls localhost HTTP |
| T9 | How do we bundle Python (FastAPI) inside an Electron app for distribution? | 🟡 Leaning toward PyInstaller | Bundle frozen Python binary with Electron; significant but solvable packaging work |
| T10 | Should skills be loaded dynamically at runtime or compiled into the agent at session start? | 🔴 Unresolved | Dynamic = more flexible; compile-time = simpler and faster |
| T11 | How do we validate module YAML files — schema validation at load time? | 🔴 Unresolved | Pydantic models for schema enforcement seem like the right call |

---

## Scope / MVP

| # | Question | Status | Notes |
|---|---|---|---|
| M1 | Which compliance module do we build first for the hackathon demo? | 🔴 Unresolved | POSH is high-impact and relatable |
| M2 | How many scenarios per module for the MVP? | 🟡 Leaning toward 2–3 | Enough to demo variety without over-building |
| M3 | Do we need a real user setup flow (resume upload) for MVP, or can we hardcode a persona? | 🔴 Unresolved | Resume upload is impressive but risky for time |
| M4 | Do we need a debrief for MVP or can we show a simple score screen? | 🔴 Unresolved | Full debrief is a key differentiator — worth the effort |

---

## Skills System

| # | Question | Status | Notes |
|---|---|---|---|
| S1 | How are skills injected into an actor's prompt — appended, prepended, or woven in? | 🔴 Unresolved | PromptBuilder utility needs a strategy here |
| S2 | Can a player "break" an actor's skill through their choices? (e.g., persistence breaks Deflection) | 🔴 Unresolved | Interesting mechanic — actors becoming more honest under pressure |
| S3 | Should skills be visible to the player (like Pokémon move lists) or hidden? | 🔴 Unresolved | Hidden feels more realistic; visible is more game-like |
| S4 | Do skills evolve during a scenario, or are they fixed at session start? | 🔴 Unresolved | Evolution = richer but complex |
| S5 | Who authors new skills — developers only, or can HR/content teams author YAML skills too? | 🔴 Unresolved | YAML authoring for non-devs is the dream; needs a good schema |

---

## Things to Think About (No Category Yet)

- The "Pokemon feel" — what visual/interaction elements make this feel like a battle and not just a chat interface? Actor avatars? Battle music? Damage flash animations?
- Observer scenarios — the player is a bystander, not the target. How does that change the option framing? ("Do nothing" becomes a valid but bad choice.)
- Accessibility — can this work for people who prefer not to read dense text quickly?
- Localization — compliance training is often region-specific (POSH is India-specific, GDPR is EU). How do modules declare their jurisdiction?
- How do we avoid the system becoming a "game to be gamed" — players optimizing for HP not learning?
- What does "free-write" evaluation look like UX-wise? A loading state while the Evaluator processes — could feel tense and dramatic if done right.
- Should the Coach Agent's debrief reference specific turns by name? ("In Step 3, when you chose to laugh it off...")
- Multi-actor scenarios where actors interact with *each other*, not just the player — does that happen? It would add realism.
