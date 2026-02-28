# Frontend API Contract

Everything the frontend needs to talk to the backend. Read this before touching any API calls.

---

## Overview

The backend runs at `http://localhost:8000` (spawned by the Electron main process on startup).

All communication happens over plain HTTP — no WebSockets, no IPC calls to the backend.
The IPC bridge (`preload.ts`) is only for Electron main ↔ renderer communication.

**Two files in this folder:**

| File | Purpose |
|---|---|
| [`types.ts`](./types.ts) | All TypeScript interfaces — import these everywhere |
| [`client.ts`](./client.ts) | Typed `api.*` functions — one per endpoint |

---

## Quick Start

```typescript
import { api } from "../../frontend-contract/client";
import type { GameState } from "../../frontend-contract/types";

// 1. Start a session
const { session_id, game_state } = await api.startSession({
  player_profile: {
    name: "Alex",
    role: "Software Engineer",
    seniority: "Mid-level",
    domain: "Technology",
    raw_context: "<resume text>",
  },
  module_id: "posh",
});

// 2. Submit a turn
const { game_state: updated } = await api.submitTurn({
  session_id,
  player_choice: "Ask Priya privately if she's okay after lunch",
});

// 3. Get the debrief (after status === "won" or "lost")
const debrief = await api.getDebrief(session_id);
```

---

## Endpoints

### `GET /health`

Check that the backend is alive. Call this on app startup before showing any UI.

```typescript
const { status } = await api.health();
// status === "ok"
```

---

### `POST /session/start`

Start a new game session. Returns the initial `GameState` including the entry-turn situation and first 3 choices.

**Request**
```typescript
{
  player_profile: {
    name: string;        // player's first name — actors use this when addressing them
    role: string;        // e.g. "Software Engineer"
    seniority: string;   // e.g. "Mid-level"
    domain: string;      // e.g. "Technology"
    raw_context: string; // full resume or JD text
  };
  module_id: string;     // e.g. "posh"
  scenario_id?: string;  // optional override; defaults to "<module_id>_bystander_001"
}
```

**Response**
```typescript
{
  session_id: string;   // store this — needed for every subsequent call
  game_state: GameState;
}
```

**When to call:** Player hits "Start" on the Setup screen.

**After the call:**
- Store `session_id` and `game_state` in the session store
- Navigate to the Arena screen
- Render `game_state.history.at(-1)` as the first turn (see [Reading Turn Data](#reading-turn-data))

---

### `POST /turn/submit`

Submit the player's choice and get the updated `GameState`.

**Request**
```typescript
{
  session_id: string;
  player_choice: string; // the label of the choice card, or the free-write text
}
```

**Response**
```typescript
{
  game_state: GameState;
}
```

**When to call:** Player clicks a choice card or submits a free-write.

**After the call, check `game_state.status`:**

| Status | Action |
|--------|--------|
| `"active"` | Render next turn in Arena (read `history.at(-1)`) |
| `"won"` | Navigate directly to Debrief screen, call `api.getDebrief()` |
| `"lost"` | Show Loss screen — two buttons: "Try again" and "See debrief" |

---

### `GET /session/{session_id}`

Fetch the current `GameState` for an existing session.

```typescript
const gameState = await api.getSession(session_id);
```

**When to call:** On reconnect or hot-reload. Not needed during normal gameplay.

---

### `POST /session/{session_id}/retry`

Reset a lost session. Same scenario, HP back to 100, step back to 0.

```typescript
const freshState = await api.retrySession(session_id);
```

**Only valid when:** `game_state.status === "lost"`.

**When to call:** Player hits "Try again" on the Loss screen.

---

### `GET /session/{session_id}/debrief`

Fetch the full Coach Agent debrief. This call is slower (2–5s in production) — show a loading state.

```typescript
const debrief = await api.getDebrief(session_id);
```

**Only valid when:** `game_state.status === "won"` or `"lost"`.

**Response shape:**
```typescript
{
  outcome: "won" | "lost";
  overall_score: number;       // 0–100
  summary: string;             // 2–3 sentence assessment
  turn_breakdowns: [
    {
      step: number;
      player_choice: string;
      what_happened: string;
      compliance_insight: string;
      hp_delta: number;
    }
  ];
  key_concepts: string[];          // compliance concepts this scenario covered
  recommended_followup: string[];  // module ids (may be empty)
}
```

---

## Reading Turn Data

The `GameState.history` array holds every turn. **The last item is always the current turn.**

```typescript
const currentTurn = gameState.history.at(-1);

currentTurn.situation         // string — narrative text to show in SituationPanel
currentTurn.choices_offered   // Choice[] — render as 3 choice cards (DO NOT show valence)
currentTurn.actor_reactions   // ActorReaction[] — actor dialogue to show in ActorPanel
```

**Important:** `Choice.valence` is on the type but must never be shown in the UI.
All three cards look identical — no hints, no colour coding.

---

## Error Handling

All `api.*` functions throw an `ApiError` on non-2xx responses.

```typescript
import { api, ApiError } from "../../frontend-contract/client";

try {
  const { game_state } = await api.submitTurn({ session_id, player_choice });
} catch (err) {
  if (err instanceof ApiError) {
    console.error(err.status, err.endpoint, err.message);
    // show error toast / retry UI
  }
}
```

Common error codes:

| Code | Meaning |
|------|---------|
| 404 | Session not found — session_id is wrong or session was cleaned up |
| 400 | Bad state — e.g. submitting a turn on a completed session, or retrying an active session |
| 422 | Missing required fields in the request body |
| 500 | Backend error — check the terminal where uvicorn is running |

---

## Full Type Reference

### `GameState`

```typescript
interface GameState {
  session_id: string;
  player_profile: PlayerProfile;
  module_id: string;       // e.g. "posh"
  scenario_id: string;     // e.g. "posh_bystander_001"
  actors: ActorInstance[]; // 1–3 actors in this scenario
  current_step: number;    // 0-indexed; starts at 0
  max_steps: number;       // typically 6
  player_hp: number;       // starts at 100, drains toward 0
  history: Turn[];         // all turns so far; last item = current turn
  status: "active" | "won" | "lost";
}
```

### `Turn`

```typescript
interface Turn {
  step: number;
  situation: string;              // narrative text for this turn
  turn_order: string[];           // actor_ids that acted, in sequence
  directives: Record<string, string>; // actor_id → directive (internal, not shown in UI)
  actor_reactions: ActorReaction[];
  choices_offered: Choice[];      // always 3
  player_choice: string;          // empty string on entry turn (step 0)
  evaluation: Evaluation | null;  // null on entry turn
  hp_delta: number;
  narrative_branch: string;       // internal label, not shown in UI
}
```

### `Choice`

```typescript
interface Choice {
  label: string;     // the text shown on the choice card
  valence: "positive" | "neutral" | "negative"; // DO NOT show to player
}
```

### `ActorReaction`

```typescript
interface ActorReaction {
  actor_id: string;  // matches an id in GameState.actors
  dialogue: string;  // the actor's in-character line this turn
}
```

### `Evaluation` (internal, feeds debrief)

```typescript
interface Evaluation {
  score: number;               // 0–100
  hp_delta: number;            // always <= 0; max -40
  reasoning: string;           // shown in Debrief, not mid-game
  is_critical_failure: boolean;
}
```

### `PlayerProfile`

```typescript
interface PlayerProfile {
  name: string;        // collected on Setup screen — actors address the player by this name
  role: string;
  seniority: string;
  domain: string;
  raw_context: string;
}
```

---

## Screen-by-Screen API Usage

### Setup Screen

```
User fills in profile + selects module
         ↓
api.health()              ← verify backend is up first
         ↓
api.startSession(...)     ← create the session
         ↓
Navigate to Arena, pass game_state + session_id via store
```

### Arena Screen

```
Render history.at(-1)  ← current situation, choices, actor reactions, HP

Player picks a choice
         ↓
api.submitTurn({ session_id, player_choice })
         ↓
Update store with new game_state
         ↓
status === "active"  → render next turn
status === "won"     → navigate to Debrief
status === "lost"    → show Loss screen
```

### Loss Screen

```
Two buttons:

[Try again]          → api.retrySession(session_id)
                       Navigate back to Arena with fresh game_state

[See debrief]        → api.getDebrief(session_id)
                       Navigate to Debrief screen
```

### Debrief Screen

```
api.getDebrief(session_id)   ← show loading state while this runs
         ↓
Render: outcome, overall_score, summary, turn_breakdowns, key_concepts
```

---

## Mock Data

The backend currently returns hardcoded data from the POSH bystander scenario ("The Uncomfortable Joke").
You do not need to configure anything — just start the backend and call the endpoints.

**The scripted narrative runs for 6 turns:**

| Step | What happens | HP delta |
|------|-------------|----------|
| 0 (entry) | Marcus cracks the joke; Claire goes quiet | 0 |
| 1 | Group laughs awkwardly; Jordan looks uncomfortable | −10 |
| 2 | Claire quietly leaves the table | −10 |
| 3 | Marcus makes another comment; Jordan pushes back mildly | −15 |
| 4 | Claire returns; private window to check in | −5 |
| 5 | HR contact in the corridor | 0 → win |

Starting HP: 100. All 5 player turns deal cumulative damage: `100 − 10 − 10 − 15 − 5 = 60 HP` at win if every turn fires.

To trigger a loss: the backend only sets `status = "lost"` if `player_hp <= 0` or a `is_critical_failure` is flagged. The mock script never flags critical failure, so a loss only occurs if you modify the mock `hp_delta` values to sum to more than −100.

---

## Running the Backend Locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # GOOGLE_API_KEY is not needed for mock mode
uvicorn api.main:app --reload --port 8000
```

The backend is ready when you see:
```
INFO:     Application startup complete.
```

Test it:
```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```
