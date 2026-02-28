"""
api/routes/session.py
---------------------
Endpoints for session lifecycle: start, status, debrief, retry.

POST /session/start        — create a new session from player profile + module
GET  /session/{id}         — get current game state
POST /session/{id}/retry   — restart the same scenario (after a loss)
GET  /session/{id}/debrief — get the Coach Agent debrief (session must be complete)

Owner: API team
Depends on: core/session_manager, utilities/session_initializer, agents/coach_agent
"""

from fastapi import APIRouter, Depends, HTTPException

from core.game_state import PlayerProfile, SessionStatus
from api.deps import (
    get_session_manager,
    get_session_initializer,
    get_coach_agent,
    get_orchestrator,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/start")
async def start_session(
    body: dict,
    session_manager=Depends(get_session_manager),
    session_initializer=Depends(get_session_initializer),
):
    """
    Body: { player_profile: PlayerProfile, module_id: str, scenario_id?: str }
    Returns: { session_id: str, game_state: GameState }
    """
    raw_profile = body.get("player_profile", {})
    player_profile = PlayerProfile(
        name=raw_profile.get("name", "there"),
        role=raw_profile.get("role", "Professional"),
        seniority=raw_profile.get("seniority", "Mid-level"),
        domain=raw_profile.get("domain", "General"),
        raw_context=raw_profile.get("raw_context", ""),
    )

    module_id = body.get("module_id", "posh")
    scenario_id = body.get("scenario_id", f"{module_id}_bystander_001")

    try:
        state = session_initializer.create_session(
            player_profile=player_profile,
            module_id=module_id,
            scenario_id=scenario_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    session_manager.create(state)
    return {"session_id": state.session_id, "game_state": state}


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    session_manager=Depends(get_session_manager),
):
    """Returns the current GameState for a session."""
    try:
        return session_manager.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")


@router.post("/{session_id}/retry")
async def retry_session(
    session_id: str,
    session_manager=Depends(get_session_manager),
    orchestrator=Depends(get_orchestrator),
    session_initializer=Depends(get_session_initializer),
):
    """
    Reset the session to step 0 with full HP, same scenario.
    Only valid when status is "lost".
    Drops and recreates actor agent ChatSessions so the retry starts fresh.
    Re-populates the entry turn from the scenario YAML.
    """
    try:
        state = session_manager.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")

    if state.status != SessionStatus.LOST:
        raise HTTPException(status_code=400, detail="Retry is only valid for lost sessions.")

    # Drop actor ChatSessions — they will be recreated on next process_turn call
    orchestrator.reset_actors(session_id)

    # Reset game state in place (clears history, HP, step)
    state = session_manager.reset(session_id)

    # Re-populate the entry turn from the YAML so actors and choices are fresh
    try:
        fresh = session_initializer.create_session(
            player_profile=state.player_profile,
            module_id=state.module_id,
            scenario_id=state.scenario_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Transplant entry turn and actors from fresh init, keep session_id
    state.history = fresh.history
    state.actors = fresh.actors
    session_manager._persist(state)  # save the entry turn back

    return state


@router.get("/{session_id}/debrief")
async def get_debrief(
    session_id: str,
    session_manager=Depends(get_session_manager),
    coach_agent=Depends(get_coach_agent),
):
    """
    Return the Coach Agent debrief.
    Only valid when status is "won" or "lost".
    """
    try:
        state = session_manager.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")

    if state.status == SessionStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Debrief is only available after the session ends.",
        )

    return await coach_agent.debrief(state)
