# Pitch — Your Cubicle Ally

> Hackathon 2026 · 3-min pitch + Q&A  
> Judging: Impact (25%) · Demo (50%) · Creativity (15%) · Pitch (10%)

---

## The Pitch (Script)

### Hook _(~15 seconds)_

> "Most compliance training is theatre. You click Next. You click Next again. You pass a quiz you could have written yourself. And three weeks later, you're in a real situation — a colleague says something wrong, a USB drive appears in the lobby, someone asks you to bend the rules for a friend — and you freeze. Because you've never actually practiced."

---

### The Problem _(~20 seconds)_

Corporate compliance training is a $3.4 billion industry that barely works:

- **Passive.** Click-through videos with no stakes. Nothing to lose, nothing to practice.
- **Identical for everyone.** The same module plays for the 10-year director and the new intern.
- **No feedback.** A quiz tells you right or wrong. It never tells you *why*, or what you should have done instead.
- **Forgotten.** Studies show 50–80% of training content is lost within a week.

Companies check a box. Nobody actually learns.

---

### The Solution _(~30 seconds)_

**Your Cubicle Ally** is compliance training that puts you in the room.

Think Pokémon PvP — but your opponent is your senior colleague making a harassment joke at team lunch, or a coworker trying to convince you to plug a mysterious USB drive into his laptop.

You see a situation. You pick from three choices — or write your own response. Your choice matters. Bad calls drain HP. The scenario actually branches based on what you do. And at the end, a Coach Agent breaks down every decision you made and explains the compliance concept behind each one.

You don't click through it. You *live* it.

---

### The Technology _(~40 seconds)_

The engine is built on **five specialized Gemini agents**:

- **Scenario Agent** — the game master. Drives the narrative, determines which characters react each turn, generates three choices calibrated to the moment.
- **Actor Agents** — up to three AI-powered characters per scenario, each with a **persistent memory** via Gemini `ChatSession`. Marcus, the colleague who made the joke, *remembers* that you called him out two turns ago. He doesn't start fresh each turn.
- **Evaluator Agent** — scores your response 0–100 against a calibrated rubric with few-shot examples. Gradient scoring — free-write answers get full credit for partial correctness, not a binary pass/fail.
- **Guardrail Agent** — validates all player input and clamps any agent outputs that fall outside expected bounds before they reach the game.
- **Coach Agent** — runs once at the end. Produces a full structured debrief: what you did well, where you slipped, the compliance concept behind each decision, and what to study next.

Actor behavior is composable through a **Skills system**: a `SocialPressure` skill makes the offender invoke group norms; `Deflection` makes them dodge accountability; `BystanderEffect` makes the quiet colleague stay silent *unless* you directly engage them. Actors are assembled from skills, not hardcoded.

Compliance content is defined in **YAML scenario files** — 13 live scenarios across 4 modules built during this hackathon:

| Module | Scenarios |
|---|---|
| POSH (Prevention of Sexual Harassment) | The Uncomfortable Joke, Microaggression in Stand-ups, Customer Crossing the Line, Team Offsite |
| Cybersecurity | USB in the Lobby, Password Reuse Boss, WiFi Trap |
| Ethics | Favor for a Friend, Data for Discount, Side Gig Conflict |
| Escalation | Informal Complaint, Retaliation Risk, Low Performer vs. Bias |

Adding a new compliance module = adding a YAML file. Zero changes to the engine.

---

### The Impact _(~20 seconds)_

Every company with more than 10 employees has mandatory training requirements. This system is built to replace passive e-learning with something people actually remember.

The architecture is white-label ready: HR teams author scenarios in YAML, add their jurisdiction's laws as module rubrics, and deploy without touching the engine. The roadmap includes a manager dashboard, RAG-grounded evaluation against live policy documents, voice interaction, and multiplayer team scenarios.

---

## Demo Flow

Run this sequence. Keep it tight — 90 seconds max.

1. **Start the server** — show `scripts/play.py` connecting to the backend (or the Electron app launching)
2. **Session setup** — enter a player name and role. Select the **POSH** module → "The Uncomfortable Joke" scenario.
3. **Turn 1** — read the situation aloud: *"It's a Friday team lunch. Marcus cracks a sexually charged joke at Claire. The table laughs awkwardly. Claire stares at her plate."* Show Marcus's reaction dialogue. Show the three choices.
4. **Pick the bad choice** — "Laugh it off and look away." Show HP drop. Emphasize: *"That's Marcus winning. We're down to 75 HP."*
5. **Turn 2** — Show the situation evolving (Marcus emboldened). Pick a good choice. Show HP hold. Show Marcus backing off in his reaction.
6. **Jump to debrief** — trigger Coach Agent. Read out one turn breakdown and the key compliance concept it surfaces.
7. **Close** — *"That's a full multi-agent compliance scenario, built in a day. 5 agents, 13 scenarios, 4 modules. Let's go."*

**Things to emphasize during demo:**
- Actor dialogue is different every run — Gemini generates it in character, in context
- The scenario branches — choices have visible consequences in the next situation
- The debrief is substantive — it references specific turns and explains the *law*, not just the outcome

---

## Judging Criteria — What to Hit

### Impact (25%)
- $3.4B compliance training market; the core product is broken and nobody has fixed it with AI yet
- Every organization has mandatory requirements — POSH in India, GDPR in EU, SOC2 + EEOC in US
- Architecture scales to any compliance domain without core changes; jurisdictions are just a module field
- Long-term: manager dashboard, team scenario data, adaptive difficulty based on historical performance
- This isn't a demo toy — the engine is production-architecture quality: persistent sessions in SQLite, full agent orchestration pipeline, typed API contract between frontend and backend

### Demo (50%)
- End-to-end functional: session start → multi-turn scenario → structured debrief
- Actor agents have genuine memory — call this out explicitly
- Gradient scoring on free-write — show a partially correct free-write response and explain the score
- 13 scenarios across 4 modules — show the module selector to signal breadth
- The Guardrail Agent protects the system from prompt injection and garbage input — mention it

### Creativity (15%)
- Multi-actor scenarios: it's not a 1v1 — it's a room. Bystanders can be pulled in. They follow your lead.
- Skills are composable behavioral bundles. Marcus's `SocialPressure` + `Deflection` combination is specifically designed to make him hard to confront — it's a designed game mechanic built from reusable primitives
- The Scenario Agent dynamically determines turn order each turn — who speaks, who stays silent, who reacts to whom. It creates genuine narrative texture without scripting
- Early resolution: if you nail it in 3 turns, the scenario can end — good behavior isn't just scored, it changes the outcome

### Pitch (10%)
- Lead with the problem, not the tech
- Let the demo do the talking — don't narrate what they can see
- End on the roadmap: *"What you've seen is the engine. The roadmap is a platform."*

---

## Anticipated Q&A

**Why Gemini?**
> The Gemini SDK gives us `ChatSession` natively — each Actor Agent has a persistent conversation history that Gemini manages, which is exactly what we need for character memory. JSON mode handles structured agent output. And Gemini 2.0 Flash image gen handles character sprites — same SDK, zero extra dependencies.

**How do you prevent hallucination or off-script agent behavior?**
> Three layers: (1) the Guardrail Agent validates all player input before any other agent sees it, and clamps any out-of-bounds agent outputs. (2) The Evaluator is grounded in scenario-specific rubrics and few-shot examples, not free-form judgment. (3) Actor prompts are constructed by the PromptBuilder at session start — persona, role, personality, and skills are all locked in before the first turn.

**How does a new compliance module get added?**
> Drop a YAML file in the `modules/` directory. The ModuleLoader picks it up at startup. The scenario defines actors, rubric, goal, few-shot evaluation examples, and entry situation. No core code changes.

**What's the business model?**
> SaaS per-seat licensing, or white-label enterprise deployment. HR/L&D teams author their own scenarios via a module builder. We handle the engine, they handle the content.

**What's left to build?**
> The frontend UI is stubbed — the backend is demo-ready and we're running it via CLI right now. Remaining: Electron Arena screen, resume parsing, and polish. Roadmap: manager dashboard, RAG-grounded evaluator, voice mode, multiplayer.

**Could someone game it by always picking the "obvious" good choice?**
> Gradient scoring makes it harder than it looks — the three choices aren't labeled by valence. You don't know which is positive. Early turns are deliberately ambiguous. And free-write responses are scored 0–100, so a technically correct but tepid answer still costs HP.

---

## One-Liners (for closing, transitions, or if you blank)

- *"Compliance training you can lose at. That's how you know it's working."*
- *"We didn't build a quiz. We built a room full of coworkers. And one of them is making everyone uncomfortable."*
- *"Marcus is powered by Gemini. He has memory, a personality, and a Deflection skill. He's a better actor than most compliance training videos."*
- *"13 scenarios, 5 agents, 4 compliance modules. Built today."*
