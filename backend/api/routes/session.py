"""
api/routes/session.py
---------------------
Endpoints for session lifecycle: start, status, debrief, restart.

POST /session/start      — create a new session from player profile + module
GET  /session/{id}       — get current game state
POST /session/{id}/retry — restart the same scenario (after a loss)
GET  /session/{id}/debrief — get the Coach Agent debrief (session must be complete)

Owner: API team
Depends on: core/session_manager, utilities/session_initializer, agents/coach_agent
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/start")
async def start_session(body: dict):
    """
    Body: { player_profile: PlayerProfile, module_id: str }
    Returns: { session_id: str, game_state: GameState }

    TODO: call SessionInitializer, create GameState, return initial situation + choices.
    """
    raise NotImplementedError


@router.get("/{session_id}")
async def get_session(session_id: str):
    """
    Returns the current GameState for a session.

    TODO: fetch from SessionManager and return.
    """
    raise NotImplementedError


@router.post("/{session_id}/retry")
async def retry_session(session_id: str):
    """
    Reset the session to step 0 with full HP, same scenario.
    Only valid when status is "lost".

    Steps:
      1. orchestrator.reset_actors(session_id) — clears ChatSession history
      2. session_manager.reset(session_id) — resets HP, step, history, status to ACTIVE

    TODO: implement reset logic in SessionManager and wire up orchestrator.
    """
    raise NotImplementedError


@router.get("/{session_id}/debrief")
async def get_debrief(session_id: str):
    """
    Run the Coach Agent and return the debrief.
    Only valid when status is "won" or "lost".

    TODO: call CoachAgent.debrief(state) and return result.
    """
    raise NotImplementedError
