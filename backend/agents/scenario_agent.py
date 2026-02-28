"""
agents/scenario_agent.py
------------------------
The orchestrator / game master agent. Drives the narrative,
determines turn order and actor directives, and generates the
next 3 player choices.

Uses the Gemini SDK (google-genai) with JSON response mode.

Output contract:
  {
    turn_order: list[str],          # actor_ids in sequence for this turn
    directives: dict[str, str],     # actor_id → instruction for this turn
    situation_summary: str,         # narrative shown to the player
    next_choices: list[Choice],     # 3 options: positive / neutral / negative
    branch_taken: str               # internal narrative branch label
  }

Owner: Agents team
Depends on: core/game_state, utilities/prompt_builder
Depended on by: core/orchestrator
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional
from google import genai
from google.genai import types

from core.game_state import GameState, Evaluation, Choice
from utilities.prompt_builder import PromptBuilder


@dataclass
class ScenarioOutput:
    turn_order: list[str]
    directives: dict[str, str]
    situation_summary: str
    next_choices: list[Choice]
    branch_taken: str
    early_resolution: bool = False


@dataclass
class PlayerDrift:
    """
    Snapshot of the player's recent performance pattern.
    Computed by the Orchestrator before each Scenario Agent call.

    Levels:
      on_track   — no notable failure pattern; proceed normally.
      passive    — 2+ consecutive sub-50 turns; create a visible intervention window.
      struggling — 3+ consecutive sub-50 turns or recent avg < 30; show cost of inaction.
      critical   — 2+ consecutive sub-20 turns; insert a pivot moment, easiest positive choice.
    """
    level: str              # "on_track" | "passive" | "struggling" | "critical"
    consecutive_poor: int   # turns in a row with score < 50
    consecutive_bad: int    # turns in a row with score < 20
    recent_avg_score: float # avg score over last ≤3 scored turns
    hp_trend: int           # sum of hp_deltas over the same window


def _format_drift_block(drift: PlayerDrift) -> str:
    """Build the [PLAYER DRIFT] paragraph injected into the Scenario Agent user message."""
    if drift.level == "on_track":
        return ""

    stats = (
        f"Recent avg score: {drift.recent_avg_score:.0f}/100 | "
        f"{drift.consecutive_poor} consecutive sub-50 turn(s) | "
        f"HP trend over last turns: {drift.hp_trend:+d}"
    )

    instructions: dict[str, str] = {
        "passive": (
            "Create a visible, natural window for intervention this turn. "
            "An actor shows a moment of distress, glances at the player, or offers a private aside "
            "that invites stepping up. The positive choice label should feel low-stakes and human "
            "(e.g. 'Check in with them quietly', 'Say something brief'). "
            "Do NOT escalate narrative pressure yet."
        ),
        "struggling": (
            "Show the concrete cost of inaction through the scene itself — the target is visibly affected, "
            "or another actor notices what the player has missed. "
            "The positive choice must feel achievable this turn: a private check-in, "
            "a simple 'that's not okay', or offering to walk somewhere together. "
            "The negative choice must carry a specific, visible narrative consequence in situation_summary. "
            "Give the player a clear on-ramp back without lecturing."
        ),
        "critical": (
            "Insert an unavoidable pivot moment. The target may ask directly for help, "
            "another bystander models intervention, or the silence in the room becomes conspicuous. "
            "Do NOT lecture. Do NOT break immersion. Let the scene do the correcting. "
            "The positive choice must be the most achievable it has been all scenario — "
            "a minimal but meaningful act (e.g. 'Ask if they're okay', 'Just sit with them'). "
            "The negative choice must carry an immediate, visceral narrative cost visible in situation_summary."
        ),
    }

    body = instructions.get(drift.level, "")
    return (
        f"\n[PLAYER DRIFT — {drift.level.upper()}]\n"
        f"{stats}\n"
        f"Required corrective action this turn: {body}"
    )


class ScenarioAgent:
    def __init__(self, prompt_builder: PromptBuilder):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.prompt_builder = prompt_builder

    async def advance(
        self,
        player_choice: str,
        evaluation: Evaluation,
        state: GameState,
        drift: Optional[PlayerDrift] = None,
    ) -> ScenarioOutput:
        """
        Advance the scenario after a player action.
        Determines turn order, sets directives, generates next situation + choices.

        drift — if provided, injects level-specific corrective instructions so the
                Scenario Agent steers the narrative back toward teachable moments when
                the player is consistently making poor choices.
        """
        system_prompt = self.prompt_builder.build_scenario_prompt(
            scenario_context=state.model_dump(),
            turn_history=state.history,
        )

        drift_block = _format_drift_block(drift) if drift else ""

        user_message = (
            f"Player chose: \"{player_choice}\"\n"
            f"Evaluation score: {evaluation.score}. Reasoning: {evaluation.reasoning}\n"
            f"Current step: {state.current_step} of {state.max_steps}"
            f"{drift_block}\n\n"
            "Return a JSON object with exactly these fields:\n"
            "  turn_order (list of actor_id strings — who acts this turn, in order)\n"
            "  directives (object mapping actor_id to a directive string)\n"
            "  situation_summary (str — the narrative shown to the player)\n"
            "  next_choices (list of 3 objects: { label: str, valence: 'positive'|'neutral'|'negative' })\n"
            "  branch_taken (str — internal label for the narrative branch chosen)\n"
            "  early_resolution (bool — true only if the situation is genuinely resolved and continuing would feel artificial)"
        )

        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            ),
        )

        data = json.loads(response.text)
        return ScenarioOutput(
            turn_order=data["turn_order"],
            directives=data["directives"],
            situation_summary=data["situation_summary"],
            next_choices=[Choice(**c) for c in data["next_choices"]],
            branch_taken=data["branch_taken"],
            early_resolution=bool(data.get("early_resolution", False)),
        )
