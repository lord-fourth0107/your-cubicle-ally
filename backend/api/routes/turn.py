"""
api/routes/turn.py
------------------
Endpoint for submitting a player's choice and getting the next turn.

POST /turn/submit — submit a player choice, get back the updated game state

Owner: API team
Depends on: core/orchestrator
"""

from fastapi import APIRouter, Depends, HTTPException

from core.game_state import SessionStatus
from agents.guardrail_agent import GuardrailViolation
from api.deps import get_orchestrator, get_session_manager

router = APIRouter()


@router.post("/submit")
async def submit_turn(
    body: dict,
    session_manager=Depends(get_session_manager),
    orchestrator=Depends(get_orchestrator),
):
    """
    Body: { session_id: str, player_choice: str }
    Returns: { game_state: GameState }

    Runs the full turn cycle via Orchestrator:
      1. EvaluatorAgent scores the player's choice
      2. ScenarioAgent advances the narrative
      3. ActorAgents react in sequence
      4. SessionManager persists the new GameState to SQLite
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

    try:
        updated_state = await orchestrator.process_turn(
            session_id=session_id,
            player_choice=player_choice,
        )
    except GuardrailViolation as exc:
        raise HTTPException(status_code=422, detail=exc.message)

    return {"game_state": updated_state}
