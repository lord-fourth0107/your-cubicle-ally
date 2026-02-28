# Future Extensions

Ideas and enhancements beyond the MVP — tracked for presentation and roadmap purposes.
These are validated directions, not speculation. Each one has a clear "why" and a realistic path to implementation.

---

## Content & Modules

| # | Idea | Origin | Why It's Compelling |
|---|---|---|---|
| F1 | **Configurable content intensity** — a `tone` field in module YAML (`"restrained"` or `"clinical"`) lets organizations tune how realistic/uncomfortable scenarios feel | P10 decision | Enterprise clients will have different policies; one size won't fit all |
| F2 | **Custom module builder** — HR/L&D teams author their own scenarios via a UI, no YAML editing required | COMPONENTS.md | Unlocks the platform for any compliance topic, not just bundled ones |
| F3 | **Jurisdiction-aware modules** — modules declare a `jurisdiction` field (e.g. `IN`, `EU`, `US`) so POSH (India), GDPR (EU), and EEOC (US) can coexist in the same registry | OPEN_QUESTIONS.md | Compliance law is region-specific; a global org needs region-specific training |

---

## Gameplay & Mechanics

| # | Idea | Origin | Why It's Compelling |
|---|---|---|---|
| F4 | **Skill visibility toggle** — let the player optionally reveal actor skills (like a Pokédex entry) as a "study mode" vs. hidden in "challenge mode" | S3 decision | Gives the tool a dual mode: learning vs. assessment |
| F5 | **Skill evolution mid-scenario** — actor skills shift based on player behavior (e.g. persistent good responses gradually break a `Deflection` skill) | S2/S4 | Makes actors feel alive and responsive to the player's choices, not just static |
| F6 | **Soft timer mode** — optional visible countdown per turn with no penalty, adding urgency for orgs that want time-pressure training | P9 decision | Some use cases (e.g. customer support training) genuinely benefit from pace pressure |
| F7 | **HP recovery on excellent answers** — small HP gain for exceptional responses, rewarding mastery not just punishing mistakes | P3 decision | Adds a positive feedback loop and incentivizes excellence over just avoiding errors |

---

## Platform & Experience

| # | Idea | Origin | Why It's Compelling |
|---|---|---|---|
| F8 | **Manager dashboard** — aggregated view of team debrief results across all sessions | ARCHITECTURE.md | Closes the loop for L&D — managers can see where their team is struggling |
| F9 | **Voice interaction mode** — actors speak in character, player responds by voice | ARCHITECTURE.md | Dramatically increases realism for communication/soft-skills training |
| F10 | **Multiplayer / team scenarios** — multiple players in the same scenario room, each making decisions that affect others | ARCHITECTURE.md | Enables group training sessions and surfaces team dynamics |
| F11 | **Replay mode** — after debrief, player can replay the scenario and see how different choices would have branched | General | Powerful learning tool — lets players explore the decision tree after the fact |
| F12 | **Web version** — browser-based companion to the Electron app for orgs that can't install desktop software | General | Broadens reach significantly; Electron architecture already separates frontend from backend cleanly |

---

## Agent Intelligence

| # | Idea | Origin | Why It's Compelling |
|---|---|---|---|
| F13 | **RAG-grounded Evaluator** — Evaluator Agent retrieves actual compliance policy text per query rather than relying on static rubrics | A7 decision | Dramatically improves accuracy and keeps evaluations current as policy changes |
| F14 | **Adaptive difficulty** — the system tunes scenario complexity based on the player's historical performance across sessions | ARCHITECTURE.md | Personalizes the challenge level over time; stops expert players from breezing through basics |
| F15 | **Actor-to-actor interaction** — actors can interact with each other in a turn, not just with the player | OPEN_QUESTIONS.md | Adds realism to group scenarios; bystanders can influence offenders before the player acts |
