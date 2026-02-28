"""
core/session_manager.py
-----------------------
Manages active game sessions. Stores and retrieves GameState,
applies turn results, and determines session end conditions.

Owner: Core team
Depends on: game_state
Depended on by: orchestrator, API routes
"""

from .game_state import GameState, Turn, SessionStatus


class SessionManager:
    def __init__(self):
        # In-memory store for active sessions.
        # TODO: back with SQLite for persistence across restarts.
        self._sessions: dict[str, GameState] = {}

    def create(self, state: GameState) -> GameState:
        """Store a new session and return it."""
        self._sessions[state.session_id] = state
        return state

    def get(self, session_id: str) -> GameState:
        """Retrieve an active session. Raises KeyError if not found."""
        return self._sessions[session_id]

    def apply_turn(self, session_id: str, turn: Turn) -> GameState:
        """
        Apply a completed turn to the session:
        - Append turn to history
        - Update player HP
        - Advance step counter
        - Evaluate win/loss conditions
        """
        state = self.get(session_id)
        state.history.append(turn)
        state.player_hp = max(0, state.player_hp + turn.hp_delta)
        state.current_step += 1

        if state.player_hp <= 0 or (turn.evaluation and turn.evaluation.is_critical_failure):
            state.status = SessionStatus.LOST
        elif state.current_step >= state.max_steps:
            state.status = SessionStatus.WON

        self._sessions[session_id] = state
        return state

    def reset(self, session_id: str) -> GameState:
        """
        Reset a lost session for retry: same scenario, HP back to 100,
        step back to 0, history cleared, status back to ACTIVE.
        Actors are reset separately via Orchestrator.reset_actors().
        """
        state = self.get(session_id)
        state.player_hp = 100
        state.current_step = 0
        state.history = []
        state.status = SessionStatus.ACTIVE
        # Clear actor memory so actors start fresh too
        for actor in state.actors:
            actor.memory = []
            actor.current_directive = ""
        self._sessions[session_id] = state
        return state

    def delete(self, session_id: str) -> None:
        """Clean up a completed session."""
        self._sessions.pop(session_id, None)
