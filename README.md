# Your Cubicle Ally

> A Pokemon PvP-style interactive compliance training system powered by AI agents.
> Hackathon 2026

Employees battle through real workplace scenarios — making choices that matter, taking damage for bad ones, and walking away with genuine learning.

---

## How It Works

1. **Setup** — Player uploads their resume or job description, selects a compliance module (POSH, Security, etc.)
2. **Battle** — A scenario plays out across 5–8 turns. Actor agents play characters in the scene. The player picks from 3 action choices or writes their own. Bad choices drain HP.
3. **Debrief** — Win or lose, the Coach Agent delivers a full breakdown: what went well, what went wrong, and the compliance concepts behind every decision.

---

## Repo Structure

```
your-cubicle-ally/
├── backend/           # Python / FastAPI — agents, game engine, API
├── frontend/          # Electron + React — the game environment
├── frontend-contract/ # Shared TypeScript types and typed API client
├── scripts/           # CLI test harness (play.py) for backend testing
└── planning/          # Design docs, architecture, open questions
```

## Quick Start

See [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md) for setup instructions.

To test the backend without a frontend, run the CLI test harness:

```bash
cd backend && uvicorn api.main:app --reload --port 8000
# in a second terminal:
python scripts/play.py
```

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before writing any code.
It has the workstream breakdown, ownership map, rules, and mock data for frontend dev.

## Planning & Design

All architecture decisions and open questions live in [`planning/`](planning/README.md).
