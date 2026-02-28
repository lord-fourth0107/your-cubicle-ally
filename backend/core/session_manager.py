"""
core/session_manager.py
-----------------------
Manages active game sessions. Stores and retrieves GameState,
applies turn results, and determines session end conditions.

Persistence: SQLite via the standard library sqlite3 module.
The database file is created at backend/sessions.db on first use.
In-memory sessions dict is kept as a read-through cache so hot
sessions avoid hitting the DB on every turn.

Owner: Core team
Depends on: game_state
Depended on by: orchestrator, API routes
"""

import sqlite3
from pathlib import Path
from .game_state import GameState, Turn, SessionStatus


DB_PATH = Path(__file__).parent.parent / "sessions.db"


class SessionManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._cache: dict[str, GameState] = {}
        self._init_db()

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id   TEXT PRIMARY KEY,
                    game_state   TEXT NOT NULL,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _persist(self, state: GameState) -> None:
        """Write a GameState to the DB (upsert)."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, game_state, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    game_state = excluded.game_state,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (state.session_id, state.model_dump_json()),
            )

    def _load_from_db(self, session_id: str) -> GameState:
        """Read a GameState from DB. Raises KeyError if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT game_state FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Session {session_id!r} not found.")
        return GameState.model_validate_json(row["game_state"])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self, state: GameState) -> GameState:
        """Store a new session and return it."""
        self._cache[state.session_id] = state
        self._persist(state)
        return state

    def get(self, session_id: str) -> GameState:
        """
        Retrieve an active session.
        Hits the in-memory cache first; falls back to SQLite.
        Raises KeyError if not found in either.
        """
        if session_id in self._cache:
            return self._cache[session_id]
        state = self._load_from_db(session_id)
        self._cache[session_id] = state
        return state

    def apply_turn(self, session_id: str, turn: Turn) -> GameState:
        """
        Apply a completed turn to the session:
        - Append turn to history
        - Update player HP
        - Advance step counter
        - Evaluate win/loss conditions
        - Persist to SQLite
        """
        state = self.get(session_id)
        # Gameplay rule:
        # - Wrong answers reduce HP.
        # - Correct answers do not heal HP.
        # - HP is capped at 100.
        effective_delta = min(0, turn.hp_delta)
        turn.hp_delta = effective_delta
        if turn.evaluation is not None:
            turn.evaluation.hp_delta = effective_delta

        state.history.append(turn)
        state.player_hp = max(0, min(100, state.player_hp + effective_delta))
        state.current_step += 1

        if state.player_hp <= 0 or (turn.evaluation and turn.evaluation.is_critical_failure):
            state.status = SessionStatus.LOST
        elif state.current_step >= state.max_steps or turn.resolved_early:
            state.status = SessionStatus.WON

        self._cache[session_id] = state
        self._persist(state)
        return state

    def reset(self, session_id: str) -> GameState:
        """
        Reset a lost session for retry: same scenario, HP back to 100,
        step back to 0, history cleared, status back to ACTIVE.
        Actor memory is cleared here; the Orchestrator recreates ChatSessions.
        """
        state = self.get(session_id)
        state.player_hp = state.starting_hp
        state.current_step = 0
        state.history = []
        state.status = SessionStatus.ACTIVE
        for actor in state.actors:
            actor.memory = []
            actor.current_directive = ""

        self._cache[session_id] = state
        self._persist(state)
        return state

    def delete(self, session_id: str) -> None:
        """Clean up a completed session from both cache and DB."""
        self._cache.pop(session_id, None)
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
