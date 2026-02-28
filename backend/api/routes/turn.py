"""
api/routes/turn.py
------------------
Endpoint for submitting a player's choice and getting the next turn.

POST /turn/submit — submit a player choice, get back the updated game state

Owner: API team
Depends on: core/orchestrator
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/submit")
async def submit_turn(body: dict):
    """
    Body: { session_id: str, player_choice: str }
    Returns: { game_state: GameState }

    The game_state includes the new situation, next choices, updated HP,
    and actor reactions for the turn that just completed.

    If game_state.status is "won" or "lost", the frontend should
    route to the debrief screen (or retry screen on loss).

    TODO: call Orchestrator.process_turn(session_id, player_choice).
    """
    raise NotImplementedError
