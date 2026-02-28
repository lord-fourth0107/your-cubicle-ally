/**
 * frontend-contract/client.ts
 * ---------------------------
 * Typed API client for the Your Cubicle Ally backend.
 * All requests go to http://localhost:8000 (backend spawned by Electron main process).
 *
 * Usage (copy into store/sessionStore.ts or use directly):
 *
 *   import { api } from "../../../frontend-contract/client";
 *
 *   const { session_id, game_state } = await api.startSession({
 *     player_profile: { role: "Engineer", seniority: "Mid-level", domain: "Tech", raw_context: "" },
 *     module_id: "posh",
 *   });
 *
 * All functions throw an ApiError on non-2xx responses.
 * Catch it to show error state in the UI.
 */

import type {
  HealthResponse,
  StartSessionRequest,
  StartSessionResponse,
  SubmitTurnRequest,
  SubmitTurnResponse,
  GameState,
  DebriefResponse,
} from "./types";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const BASE_URL = "http://localhost:8000";

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly endpoint: string,
    message: string
  ) {
    super(`[${status}] ${endpoint} — ${message}`);
    this.name = "ApiError";
  }
}

// ---------------------------------------------------------------------------
// Internal fetch helper
// ---------------------------------------------------------------------------

async function request<T>(
  method: "GET" | "POST",
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const data = await res.json();
      message = data?.detail ?? message;
    } catch {
      // ignore parse error — use statusText
    }
    throw new ApiError(res.status, path, message);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// API surface — one function per endpoint
// ---------------------------------------------------------------------------

export const api = {
  /**
   * GET /health
   * Check that the backend is up before starting a session.
   */
  health(): Promise<HealthResponse> {
    return request<HealthResponse>("GET", "/health");
  },

  /**
   * POST /session/start
   * Create a new game session from a player profile and a module.
   * Returns the initial GameState including the entry-turn situation and first 3 choices.
   *
   * When to call: player hits "Start" on the Setup screen after filling in their profile.
   *
   * Example:
   *   const { session_id, game_state } = await api.startSession({
   *     player_profile: {
   *       role: "Software Engineer",
   *       seniority: "Mid-level",
   *       domain: "Technology",
   *       raw_context: "<full resume text>",
   *     },
   *     module_id: "posh",
   *   });
   *   // Navigate to Arena screen, store session_id and game_state
   */
  startSession(body: StartSessionRequest): Promise<StartSessionResponse> {
    return request<StartSessionResponse>("POST", "/session/start", body);
  },

  /**
   * GET /session/{session_id}
   * Fetch the current GameState for an existing session.
   * Useful on reload / reconnect — not needed during normal turn-by-turn flow.
   */
  getSession(sessionId: string): Promise<GameState> {
    return request<GameState>("GET", `/session/${sessionId}`);
  },

  /**
   * POST /turn/submit
   * Submit the player's choice for the current turn.
   * Returns the updated GameState with the next situation, choices, and actor reactions.
   *
   * When to call: player clicks a choice card or submits a free-write.
   *
   * After receiving the response:
   *   - Update stored game_state
   *   - Read game_state.history.at(-1) for the new turn data
   *   - If game_state.status === "won"  → navigate to Debrief screen
   *   - If game_state.status === "lost" → show Loss screen (retry or debrief)
   *   - If game_state.status === "active" → render next turn in Arena
   *
   * Example:
   *   const { game_state } = await api.submitTurn({
   *     session_id: "abc-123",
   *     player_choice: "Ask Priya privately if she's okay after lunch",
   *   });
   */
  submitTurn(body: SubmitTurnRequest): Promise<SubmitTurnResponse> {
    return request<SubmitTurnResponse>("POST", "/turn/submit", body);
  },

  /**
   * POST /session/{session_id}/retry
   * Reset a lost session: same scenario, HP back to 100, step back to 0.
   * Only valid when game_state.status === "lost".
   * Returns the reset GameState (ready for turn 0 again).
   *
   * When to call: player hits "Try again" on the Loss screen.
   */
  retrySession(sessionId: string): Promise<GameState> {
    return request<GameState>("POST", `/session/${sessionId}/retry`);
  },

  /**
   * GET /session/{session_id}/debrief
   * Run the Coach Agent and return the full debrief.
   * Only valid when game_state.status === "won" or "lost".
   * This is a slower call (~2–5s) — show a loading state.
   *
   * When to call:
   *   - Automatically after status === "won"
   *   - When player hits "See debrief" on the Loss screen
   */
  getDebrief(sessionId: string): Promise<DebriefResponse> {
    return request<DebriefResponse>("GET", `/session/${sessionId}/debrief`);
  },
};
