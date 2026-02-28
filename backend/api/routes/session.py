"""
api/routes/session.py
---------------------
Endpoints for session lifecycle: start, status, debrief, restart.

POST /session/start        — create a new session from player profile + module
GET  /session/{id}         — get current game state
POST /session/{id}/retry   — restart the same scenario (after a loss)
GET  /session/{id}/debrief — get the Coach Agent debrief (session must be complete)

Owner: API team
Depends on: core/session_manager, utilities/session_initializer, agents/coach_agent

NOTE: All routes currently return MOCK DATA using the POSH bystander scenario.
      Replace each handler body with the real implementation once the
      SessionInitializer and CoachAgent are ready. The response shape must
      not change — only the data source.
"""

import uuid
from fastapi import APIRouter, HTTPException
from ...core.game_state import (
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
# In-memory session store (mock only — real impl will use SessionManager)
# ---------------------------------------------------------------------------

_sessions: dict[str, GameState] = {}

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
    _sessions[session_id] = game_state

    return {"session_id": session_id, "game_state": game_state}


@router.get("/{session_id}")
async def get_session(session_id: str):
    """
    Returns the current GameState for a session.

    Real impl: fetch from SessionManager.
    """
    state = _sessions.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")
    return state


@router.post("/{session_id}/retry")
async def retry_session(session_id: str):
    """
    Reset the session to step 0 with full HP, same scenario.
    Only valid when status is "lost".

    Real impl: call orchestrator.reset_actors() then session_manager.reset().
    """
    state = _sessions.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")
    if state.status != SessionStatus.LOST:
        raise HTTPException(status_code=400, detail="Retry is only valid for lost sessions.")

    fresh = _make_fresh_game_state(session_id, state.player_profile)
    _sessions[session_id] = fresh
    return fresh


@router.get("/{session_id}/debrief")
async def get_debrief(session_id: str):
    """
    Return the Coach Agent debrief.
    Only valid when status is "won" or "lost".

    Real impl: call CoachAgent.debrief(state).
    """
    state = _sessions.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")
    if state.status == SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Debrief is only available after the session ends.")

    # Build mock turn breakdowns from history (skipping entry turn which has no player_choice)
    turn_breakdowns = []
    for turn in state.history:
        if not turn.player_choice:
            continue
        turn_breakdowns.append({
            "step": turn.step,
            "player_choice": turn.player_choice,
            "what_happened": turn.situation,
            "compliance_insight": (
                turn.evaluation.reasoning
                if turn.evaluation
                else "No evaluation recorded for this turn."
            ),
            "hp_delta": turn.hp_delta,
        })

    overall_score = max(0, state.player_hp)
    outcome = state.status.value  # "won" or "lost"

    return {
        "outcome": outcome,
        "overall_score": overall_score,
        "summary": (
            f"You finished the scenario with {state.player_hp} HP remaining. "
            "Your choices had real consequences for Claire and signalled to the group what kind of colleague you are. "
            "Review the turn breakdown below to understand where you could have intervened more effectively."
        ),
        "turn_breakdowns": turn_breakdowns,
        "key_concepts": [
            "Bystander intervention",
            "POSH Act reporting obligations",
            "Creating psychological safety",
            "Addressing harassment in group settings",
        ],
        "recommended_followup": ["posh_reporting_002"] if state.player_hp < 60 else [],
    }
