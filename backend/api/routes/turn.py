"""
api/routes/turn.py
------------------
Endpoint for submitting a player's choice and getting the next turn.

Uses Orchestrator.process_turn() for the multi-agent workflow.
"""

from fastapi import APIRouter, HTTPException

from api.dependencies import session_manager, orchestrator
from core.game_state import SessionStatus

router = APIRouter()


@router.post("/submit")
async def submit_turn(body: dict):
    """
    Body: { session_id: str, player_choice: str }
    Returns: { game_state: GameState }

    Uses Orchestrator.process_turn() — Evaluator, Scenario, and Actor agents
    run in sequence for each human player choice.
    """
    session_id: str = body.get("session_id", "")
    player_choice: str = body.get("player_choice", "")

    if not session_id or not player_choice:
        raise HTTPException(status_code=422, detail="session_id and player_choice are required.")

    try:
        state = session_manager.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")
    if state.status != SessionStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not active (status={state.status.value!r}). Cannot submit turn.",
        )

    updated = await orchestrator.process_turn(session_id, player_choice)
    return {"game_state": updated}
