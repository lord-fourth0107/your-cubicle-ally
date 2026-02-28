# Frontend

Electron desktop app with a React renderer. The game environment.

## Stack
- **Electron** — desktop shell, main process, child process management
- **React + TypeScript** — renderer process UI
- **Vite** — bundler for the renderer

## Structure

```
frontend/
└── src/
    ├── main/                    # Electron main process (Node.js)
    │   ├── index.ts             # App entry, window creation
    │   ├── preload.ts           # Secure IPC bridge to renderer
    │   └── server-manager.ts   # Spawns and manages the FastAPI backend
    └── renderer/                # React app (runs in Electron renderer)
        ├── screens/
        │   ├── Setup/           # Resume input + module selection
        │   ├── Arena/           # The battle UI
        │   └── Debrief/         # End-of-scenario debrief
        ├── components/
        │   ├── HPBar/           # Animated HP bar (current / max display)
        │   ├── ActorPanel/      # Actor portraits and names
        │   ├── SituationPanel/  # Narrative text display
        │   └── ChoiceCards/     # 3 choice buttons + free-write input
        ├── store/               # Global state (game state, session)
        └── App.tsx              # Root component, screen routing
```

## Setup

```bash
cd frontend
npm install
npm run dev      # starts Electron in dev mode (also starts backend)
```

## Ownership Map

| Folder | Owner | Notes |
|---|---|---|
| `main/` | Electron team | Server lifecycle, IPC, window management |
| `screens/Setup` | Setup team | Resume input, module selector |
| `screens/Arena` | Arena team | Core game loop UI |
| `screens/Debrief` | Debrief team | Debrief rendering |
| `components/HPBar` | Arena team | HP bar animation, current/max display |
| `components/ActorPanel` | Arena team | Actor portraits and names |
| `components/ChoiceCards` | Arena team | Choice selection + free-write |
| `store/` | Shared | Game state shape — don't change without discussion |

## Backend Communication

The renderer calls the FastAPI backend over `http://localhost:8000`.
All API calls must go through `frontend-contract/client.ts` — the typed API client that mirrors the backend contract exactly. Do not call the backend directly from components or stores.

## Key Contracts

- **HP display**: always show `current / max` (e.g. `65 / 100`), animate bar decrease on damage
- **Choice cards**: 3 cards always rendered — valence is NOT shown to the player
- **Loss screen**: on `status === "lost"` show two options: retry same scenario, or go to debrief
- **Win screen**: on `status === "won"` go directly to debrief
