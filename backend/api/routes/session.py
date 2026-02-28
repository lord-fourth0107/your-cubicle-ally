"""
api/routes/session.py
---------------------
Endpoints for session lifecycle: start, status, debrief, restart.

Uses SessionManager, Orchestrator, CoachAgent for the multi-agent workflow.
"""

import uuid
from fastapi import APIRouter, HTTPException

from api.dependencies import session_manager, orchestrator, coach_agent
from core.game_state import (
    GameState,
    SessionStatus,
    PlayerProfile,
    ActorInstance,
    Turn,
    Choice,
    ActorReaction,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Mock scenario data — POSH bystander 001 "The Uncomfortable Joke"
# ---------------------------------------------------------------------------

_MOCK_ACTORS = [
    ActorInstance(
        actor_id="marcus",
        persona="A confident, socially dominant mid-level colleague who doesn't believe he's done anything wrong.",
        role="The offender. Makes a sexually charged joke at a team lunch and deflects any pushback with humour.",
        personality="Charming, self-assured, minimises conflict by reframing it as oversensitivity.",
        skills=["social_pressure", "deflection"],
        tools=[],
        memory=[],
        current_directive="",
    ),
    ActorInstance(
        actor_id="claire",
        persona="A reserved, professional newer team member who is the target of the joke.",
        role="The target. She is visibly uncomfortable but hesitant to make a scene in a group setting.",
        personality="Quietly composed, doesn't want to cause conflict, but will open up if given a safe space.",
        skills=["hesitation"],
        tools=[],
        memory=[],
        current_directive="",
    ),
    ActorInstance(
        actor_id="jordan",
        persona="A quiet bystander who laughed along but privately feels uneasy.",
        role="The bystander. Will follow the player's lead if directly engaged.",
        personality="Conflict-averse, goes along with the group, but has a conscience.",
        skills=["bystander_effect", "hesitation"],
        tools=[],
        memory=[],
        current_directive="",
    ),
]

_ENTRY_TURN = Turn(
    step=0,
    situation=(
        "It's a Friday team lunch at a restaurant. The mood is relaxed. "
        "Marcus, your senior colleague, cracks a sexually charged joke loosely directed at Claire. "
        "The table laughs awkwardly. Claire goes quiet and stares at her plate. "
        "Everyone is waiting to see what happens next."
    ),
    turn_order=["marcus"],
    directives={"marcus": "Make the joke and look pleased with yourself."},
    actor_reactions=[
        ActorReaction(
            actor_id="marcus",
            dialogue="Relax, it's just a joke. Everyone's so sensitive these days.",
        )
    ],
    choices_offered=[
        Choice(label="Ask Claire privately if she's okay after lunch", valence="positive"),
        Choice(label="Change the subject loudly to break the tension", valence="neutral"),
        Choice(label="Laugh it off and look away", valence="negative"),
    ],
    player_choice="",
    evaluation=None,
    hp_delta=0,
    narrative_branch="entry",
)


def _make_fresh_game_state(session_id: str, player_profile: PlayerProfile) -> GameState:
    return GameState(
        session_id=session_id,
        player_profile=player_profile,
        module_id="posh",
        scenario_id="posh_bystander_001",
        actors=[a.model_copy(deep=True) for a in _MOCK_ACTORS],
        current_step=0,
        max_steps=6,
        player_hp=100,
        history=[_ENTRY_TURN.model_copy(deep=True)],
        status=SessionStatus.ACTIVE,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/start")
async def start_session(body: dict):
    """
    Body: { player_profile: PlayerProfile, module_id: str }
    Returns: { session_id: str, game_state: GameState }

    Mock: ignores module_id and always loads the POSH bystander scenario.
    Real impl: call SessionInitializer with the supplied module_id.
    """
    raw_profile = body.get("player_profile", {})
    player_profile = PlayerProfile(
        name=raw_profile.get("name", "there"),
        role=raw_profile.get("role", "Professional"),
        seniority=raw_profile.get("seniority", "Mid-level"),
        domain=raw_profile.get("domain", "General"),
        raw_context=raw_profile.get("raw_context", ""),
    )

    session_id = str(uuid.uuid4())
    game_state = _make_fresh_game_state(session_id, player_profile)
    session_manager.create(game_state)

    return {"session_id": session_id, "game_state": game_state}


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Returns the current GameState for a session."""
    try:
        return session_manager.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")


@router.post("/{session_id}/retry")
async def retry_session(session_id: str):
    """
    Reset the session to step 0 with full HP, same scenario.
    Only valid when status is "lost".
    """
    try:
        state = session_manager.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")
    if state.status != SessionStatus.LOST:
        raise HTTPException(status_code=400, detail="Retry is only valid for lost sessions.")

    orchestrator.reset_actors(session_id)
    fresh = _make_fresh_game_state(session_id, state.player_profile)
    session_manager.create(fresh)
    return fresh


@router.get("/{session_id}/debrief")
async def get_debrief(session_id: str):
    """
    Return the Coach Agent debrief.
    Only valid when status is "won" or "lost".
    """
    try:
        state = session_manager.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")
    if state.status == SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Debrief is only available after the session ends.")

    return await coach_agent.debrief(state)
