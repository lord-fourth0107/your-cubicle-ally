/**
 * store/gameStore.ts
 * ------------------
 * Global game state store for the renderer process.
 * Holds the current GameState returned from the backend after each turn.
 *
 * Owner: Frontend team
 * Depends on: nothing (pure state)
 * Depended on by: Arena screen, HP bar, choice cards, debrief screen
 *
 * TODO: implement using Zustand or similar lightweight state manager.
 *
 * Shape mirrors the backend GameState Pydantic model:
 *   session_id, player_profile, module_id, scenario_id,
 *   actors, current_step, max_steps, player_hp, history, status
 */

export type SessionStatus = "active" | "won" | "lost" | "complete";

export interface Choice {
  label: string;
  valence: "positive" | "neutral" | "negative";
}

export interface ActorReaction {
  actor_id: string;
  dialogue: string;
}

export interface GameState {
  session_id: string;
  player_hp: number;
  max_hp: number;
  current_step: number;
  max_steps: number;
  status: SessionStatus;
  current_situation: string;
  current_choices: Choice[];
  current_actor_reactions: ActorReaction[];
}

// TODO: implement store actions:
//   - setGameState(state: GameState)
//   - clearSession()
