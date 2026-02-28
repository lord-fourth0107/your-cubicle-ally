/**
 * frontend-contract/types.ts
 * --------------------------
 * Single source of truth for all types shared between the frontend and backend.
 * These mirror the backend Pydantic models in backend/core/game_state.py exactly.
 *
 * DO NOT invent new shapes — if something needs to change here, update the backend model first.
 *
 * Imported by: api/client.ts, store/sessionStore.ts, and any screen/component that
 *              needs to type a prop or local variable against the API contract.
 */

// ---------------------------------------------------------------------------
// Core enums
// ---------------------------------------------------------------------------

export type SessionStatus = "active" | "won" | "lost";

export type ChoiceValence = "positive" | "neutral" | "negative";

// ---------------------------------------------------------------------------
// Sub-models (mirrors game_state.py)
// ---------------------------------------------------------------------------

export interface PlayerProfile {
  role: string;         // e.g. "Software Engineer"
  seniority: string;    // e.g. "Mid-level"
  domain: string;       // e.g. "Technology"
  raw_context: string;  // full resume / JD text the player pasted in
}

export interface Choice {
  label: string;
  /**
   * Valence is present on the type but MUST NOT be shown to the player in the UI.
   * It is returned by the backend for internal tracking only.
   * The Arena screen renders all three choices identically — no hints.
   */
  valence: ChoiceValence;
}

export interface Evaluation {
  score: number;              // 0–100
  hp_delta: number;           // always <= 0 (drain only); max penalty is -40
  reasoning: string;          // fed into Coach Agent debrief — not shown mid-game
  is_critical_failure: boolean;
}

export interface ActorReaction {
  actor_id: string;
  dialogue: string;           // the actor's in-character response this turn
}

export interface Message {
  role: "system" | "user" | "assistant" | "model";
  content: string;
}

export interface ActorInstance {
  actor_id: string;
  persona: string;
  role: string;
  personality: string;
  skills: string[];           // skill ids (e.g. "deflection", "empathy")
  tools: string[];
  memory: Message[];
  current_directive: string;
}

export interface Turn {
  step: number;
  situation: string;          // narrative text shown to the player this turn
  turn_order: string[];       // actor_ids that acted this turn, in sequence
  directives: Record<string, string>; // actor_id → directive
  actor_reactions: ActorReaction[];
  choices_offered: Choice[];  // always 3 options
  player_choice: string;      // empty string on the entry turn (step 0)
  evaluation: Evaluation | null; // null on the entry turn
  hp_delta: number;
  narrative_branch: string;
}

// ---------------------------------------------------------------------------
// GameState — the canonical response shape for all session endpoints
// ---------------------------------------------------------------------------

/**
 * GameState is returned by:
 *   POST /session/start    (inside StartSessionResponse)
 *   GET  /session/{id}
 *   POST /session/{id}/retry
 *   POST /turn/submit      (inside SubmitTurnResponse)
 *
 * Reading current turn data from GameState:
 *   const currentTurn = gameState.history.at(-1);
 *   currentTurn.situation        → narrative text for this turn
 *   currentTurn.choices_offered  → 3 choices (DO NOT show valence in UI)
 *   currentTurn.actor_reactions  → actor dialogue to render in ActorPanel
 */
export interface GameState {
  session_id: string;
  player_profile: PlayerProfile;
  module_id: string;
  scenario_id: string;
  actors: ActorInstance[];
  current_step: number;       // 0-indexed; starts at 0
  max_steps: number;          // typically 6
  player_hp: number;          // starts at 100, drains toward 0
  history: Turn[];            // all completed turns; last item = current turn
  status: SessionStatus;
}

// ---------------------------------------------------------------------------
// Debrief — returned by GET /session/{id}/debrief
// ---------------------------------------------------------------------------

export interface TurnBreakdown {
  step: number;
  player_choice: string;
  what_happened: string;
  compliance_insight: string;
  hp_delta: number;
}

export interface DebriefResponse {
  outcome: "won" | "lost";
  overall_score: number;        // 0–100
  summary: string;              // 2–3 sentence overall assessment
  turn_breakdowns: TurnBreakdown[];
  key_concepts: string[];       // compliance concepts this scenario covered
  recommended_followup: string[]; // module ids worth trying next (may be empty)
}

// ---------------------------------------------------------------------------
// Request / Response shapes per endpoint
// ---------------------------------------------------------------------------

/** POST /session/start */
export interface StartSessionRequest {
  player_profile: PlayerProfile;
  module_id: string;
}

export interface StartSessionResponse {
  session_id: string;
  game_state: GameState;
}

/** POST /turn/submit */
export interface SubmitTurnRequest {
  session_id: string;
  player_choice: string;
}

export interface SubmitTurnResponse {
  game_state: GameState;
}

/** GET /health */
export interface HealthResponse {
  status: "ok";
}
