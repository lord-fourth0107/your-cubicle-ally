/**
 * store/gameStore.ts
 * ------------------
 * Shared frontend state types.
 *
 * Keep these as re-exports from the backend-aligned contract to avoid drift.
 * Canonical source: frontend-contract/types.ts
 */

export type {
  SessionStatus,
  Choice,
  ActorReaction,
  Turn,
  PlayerProfile,
  GameState,
} from "../../../../frontend-contract/types";
