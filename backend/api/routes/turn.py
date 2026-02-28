"""
api/routes/turn.py
------------------
Endpoint for submitting a player's choice and getting the next turn.

POST /turn/submit — submit a player choice, get back the updated game state

Owner: API team
Depends on: core/orchestrator

NOTE: This route currently uses a pre-scripted 6-turn POSH mock progression.
      Replace the handler body with a real Orchestrator.process_turn() call
      once the agents are ready. The response shape must not change.
"""

from fastapi import APIRouter, HTTPException
from .session import _sessions  # shared in-memory store (mock only)
from ...core.game_state import (
    SessionStatus,
    Turn,
    Choice,
    ActorReaction,
    Evaluation,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Pre-scripted mock turns — POSH bystander 001
# Indexed by step number (step 0 is the entry turn, so player actions start
# at step 1). Each dict represents what happens AFTER the player acts on
# the previous step's choices.
# ---------------------------------------------------------------------------

def _build_mock_turns(player_name: str) -> list[dict]:
    """Build the scripted turn sequence, personalised with the player's name."""
    return [
        # Player's first action → step 1
        {
            "situation": (
                "The group laughs awkwardly. Claire forces a smile but her eyes are down. "
                "Jordan catches your eye briefly, then looks away. "
                "Marcus is still grinning, waiting to see if anyone pushes back."
            ),
            "turn_order": ["marcus", "jordan"],
            "directives": {
                "marcus": "Look pleased. Wait for someone to validate you.",
                "jordan": "Laugh nervously. Don't commit to a side.",
            },
            "actor_reactions": [
                ActorReaction(actor_id="marcus", dialogue="See? Everyone gets it. You all just need to lighten up."),
                ActorReaction(actor_id="jordan", dialogue="I mean... haha... yeah. Anyway, should we order?"),
            ],
            "choices_offered": [
                Choice(label="Tell Marcus directly that the comment wasn't appropriate", valence="positive"),
                Choice(label="Ask Jordan quietly what he thought of that", valence="neutral"),
                Choice(label="Agree with Marcus and change the subject", valence="negative"),
            ],
            "hp_delta": -10,
            "score": 60,
            "reasoning": "Player's first action shaped the group dynamic. Failing to intervene early normalises the behaviour.",
            "is_critical_failure": False,
            "narrative_branch": "group_laughs",
        },
        # Player's second action → step 2
        {
            "situation": (
                "Claire quietly excuses herself to the bathroom. Marcus watches her go. "
                "'She'll get over it,' he says to no one in particular. "
                "Jordan shifts in his seat. This is your moment."
            ),
            "turn_order": ["marcus", "jordan"],
            "directives": {
                "marcus": "Minimise the situation. Act like Claire is overreacting.",
                "jordan": "Be visibly uncomfortable. Show you want someone to do something.",
            },
            "actor_reactions": [
                ActorReaction(actor_id="marcus", dialogue="She's always been a bit sensitive. You know how it is."),
                ActorReaction(actor_id="jordan", dialogue="I don't know... that felt like a bit much to me, honestly."),
            ],
            "choices_offered": [
                Choice(label="Follow Claire to check in with her privately", valence="positive"),
                Choice(label="Challenge Marcus's 'she'll get over it' comment", valence="neutral"),
                Choice(label="Nod and move on — it's not your place", valence="negative"),
            ],
            "hp_delta": -10,
            "score": 55,
            "reasoning": "The situation escalated with Claire leaving. A direct bystander response was available but not taken.",
            "is_critical_failure": False,
            "narrative_branch": "claire_exits",
        },
        # Player's third action → step 3
        {
            "situation": (
                "Claire returns to the table. She looks composed but quieter than before. "
                "Marcus makes another off-colour remark — smaller this time, under his breath, "
                "but you catch it. Jordan gives you a pointed look."
            ),
            "turn_order": ["marcus", "claire", "jordan"],
            "directives": {
                "marcus": "Make a quieter follow-up comment. Test whether anyone will push back.",
                "claire": "Return composed. Don't engage directly with Marcus.",
                "jordan": "Signal to the player nonverbally that someone needs to say something.",
            },
            "actor_reactions": [
                ActorReaction(actor_id="marcus", dialogue="Back already? Thought we scared you off. Ha."),
                ActorReaction(actor_id="claire", dialogue="Let's just... have a nice lunch."),
                ActorReaction(actor_id="jordan", dialogue="Marcus, come on. That's enough, yeah?"),
            ],
            "choices_offered": [
                Choice(label="Back Jordan up: 'They're right, Marcus. That's not okay.'", valence="positive"),
                Choice(label="Address Claire directly: 'You okay? We can talk later.'", valence="neutral"),
                Choice(label="Stay quiet — Jordan said something, that's enough", valence="negative"),
            ],
            "hp_delta": -15,
            "score": 40,
            "reasoning": "Marcus's continued behaviour required a direct response. A second incident without intervention signals tacit acceptance.",
            "is_critical_failure": False,
            "narrative_branch": "marcus_doubles_down",
        },
        # Player's fourth action → step 4
        {
            "situation": (
                "Lunch wraps up. The group starts heading back to the office. "
                "Claire is walking ahead on her own. You have a window to talk to her privately "
                "before the day moves on."
            ),
            "turn_order": ["claire"],
            "directives": {
                "claire": "Walk ahead. Be available to the player if approached.",
            },
            "actor_reactions": [
                ActorReaction(
                    actor_id="claire",
                    dialogue=f"Oh, hey {player_name}. I'm fine, really. Just... you know. Anyway. Thanks for asking.",
                ),
            ],
            "choices_offered": [
                Choice(
                    label="Tell Claire you saw what happened and you're happy to support a formal report",
                    valence="positive",
                ),
                Choice(label="Say you thought it was out of line and leave it at that", valence="neutral"),
                Choice(label="Say nothing — she said she's fine", valence="negative"),
            ],
            "hp_delta": -5,
            "score": 70,
            "reasoning": "Private check-in with Claire was the right instinct. Whether she was explicitly offered reporting support is what distinguishes a good response from an excellent one.",
            "is_critical_failure": False,
            "narrative_branch": "private_checkin",
        },
        # Player's fifth action → step 5 (last real turn before win/lose resolution)
        {
            "situation": (
                "Back at the office. You pass your HR contact in the corridor. "
                "She asks how the team lunch was — routine small talk. "
                "You have a choice about how much to share."
            ),
            "turn_order": [],
            "directives": {},
            "actor_reactions": [],
            "choices_offered": [
                Choice(
                    label="Tell her what happened and ask about the reporting process",
                    valence="positive",
                ),
                Choice(label="Say it was fine — you'll handle it another way", valence="neutral"),
                Choice(label="Say it was great. Move on.", valence="negative"),
            ],
            "hp_delta": 0,
            "score": 80,
            "reasoning": "The final opportunity to escalate through formal channels. Proactively raising it with HR is the gold standard bystander response.",
            "is_critical_failure": False,
            "narrative_branch": "hr_corridor",
        },
    ]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/submit")
async def submit_turn(body: dict):
    """
    Body: { session_id: str, player_choice: str }
    Returns: { game_state: GameState }

    Mock: advances through the pre-scripted POSH turn sequence.
    Real impl: call Orchestrator.process_turn(session_id, player_choice).

    Status transitions:
      - After the final mock turn (step == max_steps - 1):
          player_hp > 0  → status = "won"
          player_hp <= 0 → status = "lost"
      - Any turn where a critical failure is flagged → status = "lost" immediately
    """
    session_id: str = body.get("session_id", "")
    player_choice: str = body.get("player_choice", "")

    if not session_id or not player_choice:
        raise HTTPException(status_code=422, detail="session_id and player_choice are required.")

    state = _sessions.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found.")
    if state.status != SessionStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not active (status={state.status.value!r}). Cannot submit turn.",
        )

    # Which scripted turn comes next?
    # current_step is 0-indexed. Step 0 is the entry turn (already in history).
    # The first player action advances to step 1.
    mock_turns = _build_mock_turns(state.player_profile.name)
    script_index = state.current_step  # 0-based index into mock_turns
    if script_index >= len(mock_turns):
        raise HTTPException(status_code=400, detail="No more turns available in this session.")

    script = mock_turns[script_index]

    evaluation = Evaluation(
        score=script["score"],
        hp_delta=script["hp_delta"],
        reasoning=script["reasoning"],
        is_critical_failure=script["is_critical_failure"],
    )

    new_step = state.current_step + 1
    new_hp = max(0, state.player_hp + script["hp_delta"])

    # Stamp the player's choice and evaluation onto the current (entry) turn
    # then append the new turn that follows.
    if state.history:
        state.history[-1].player_choice = player_choice
        state.history[-1].evaluation = evaluation
        state.history[-1].hp_delta = script["hp_delta"]

    new_turn = Turn(
        step=new_step,
        situation=script["situation"],
        turn_order=script["turn_order"],
        directives=script["directives"],
        actor_reactions=script["actor_reactions"],
        choices_offered=script["choices_offered"],
        player_choice="",
        evaluation=None,
        hp_delta=0,
        narrative_branch=script["narrative_branch"],
    )

    state.history.append(new_turn)
    state.player_hp = new_hp
    state.current_step = new_step

    # Determine session end condition
    if script["is_critical_failure"] or new_hp <= 0:
        state.status = SessionStatus.LOST
    elif new_step >= state.max_steps:
        state.status = SessionStatus.WON

    _sessions[session_id] = state
    return {"game_state": state}
