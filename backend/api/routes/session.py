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
import re

from core.game_state import PlayerProfile, SessionStatus
from api.deps import (
    get_session_manager,
    get_session_initializer,
    get_coach_agent,
    get_orchestrator,
    get_module_loader,
)
from utilities.module_loader import ModuleLoader

router = APIRouter()

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _resolve_scenario_id(
    module_loader: ModuleLoader,
    module_id: str,
    scenario_id: str | None,
) -> str:
    """Use scenario_id if provided; otherwise first scenario in module."""
    if scenario_id:
        return scenario_id
    scenarios = module_loader.list_scenarios(module_id)
    if not scenarios:
        return f"{module_id}_bystander_001"  # fallback for legacy callers
    return scenarios[0]


_ROLE_HINT_WORDS = {
    "engineer", "developer", "manager", "analyst", "designer", "lead", "specialist",
    "consultant", "architect", "coordinator", "director", "administrator", "officer",
    "associate", "intern", "scientist", "owner", "technician", "accountant", "recruiter",
    "marketer", "sales", "product", "security", "hr", "finance", "operations",
    "ceo", "cto", "cfo", "coo", "cio", "cmo", "ciso", "chro", "president",
}

_JD_HINT_WORDS = {
    "responsibilities", "requirements", "experience", "skills", "qualifications", "role",
    "team", "you will", "must", "should", "years", "develop", "design", "manage", "build",
    "support", "stakeholders", "collaborate", "communication",
}


def _is_gibberish_text(text: str) -> bool:
    t = text.strip().lower()
    if not t:
        return True
    if any(bad in t for bad in ("lorem ipsum", "asdf", "qwerty", "123456", "!!@@")):
        return True
    letters = sum(ch.isalpha() for ch in t)
    if letters / max(1, len(t)) < 0.45:
        return True
    condensed = re.sub(r"\s+", "", t)
    if len(condensed) >= 8:
        unique_ratio = len(set(condensed)) / len(condensed)
        if unique_ratio < 0.18:
            return True
    return False


def _looks_like_role_title(text: str) -> bool:
    t = re.sub(r"\s+", " ", text.strip())
    if not (2 <= len(t) <= 80):
        return False
    if any(ch.isdigit() for ch in t):
        return False
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", t)]
    if not (1 <= len(words) <= 8):
        return False
    if len(words) == 1:
        return words[0] in _ROLE_HINT_WORDS
    return any(w in _ROLE_HINT_WORDS for w in words)


def _looks_like_job_description(text: str) -> bool:
    t = text.strip().lower()
    if len(t) < 40:
        return False
    tokens = re.findall(r"[a-z]+", t)
    if len(tokens) < 8:
        return False
    hits = sum(1 for hint in _JD_HINT_WORDS if hint in t)
    return hits >= 2


def _is_valid_job_input(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if _is_gibberish_text(t):
        return False
    return _looks_like_role_title(t) or _looks_like_job_description(t)


@router.post("/start")
async def start_session(
    body: dict,
    session_manager=Depends(get_session_manager),
    session_initializer=Depends(get_session_initializer),
    module_loader=Depends(get_module_loader),
):
    """
    Body: { player_profile: PlayerProfile, module_id: str, scenario_id?: str }
    Returns: { session_id: str, game_state: GameState }

    If scenario_id is omitted, uses the first scenario in the module.
    """
    raw_profile = body.get("player_profile", {})
    player_profile = PlayerProfile(
        name=raw_profile.get("name", "there"),
        role=raw_profile.get("role", "Professional"),
        seniority=raw_profile.get("seniority", "Mid-level"),
        domain=raw_profile.get("domain", "General"),
        raw_context=raw_profile.get("raw_context", ""),
    )

    if not _is_valid_job_input(player_profile.raw_context):
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid input. Please provide a valid job role title or a realistic "
                "job description in the job description field."
            ),
        )

    module_id = body.get("module_id", "posh")
    scenario_id = _resolve_scenario_id(
        module_loader,
        module_id,
        body.get("scenario_id"),
    )

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
