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
from dataclasses import dataclass
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
    ) -> ScenarioOutput:
        """
        Advance the scenario after a player action.
        Determines turn order, sets directives, generates next situation + choices.
        """
        system_prompt = self.prompt_builder.build_scenario_prompt(
            scenario_context=state.model_dump(),
            turn_history=state.history,
        )

        user_message = (
            f"Player chose: \"{player_choice}\"\n"
            f"Evaluation score: {evaluation.score}. Reasoning: {evaluation.reasoning}\n"
            f"Current step: {state.current_step} of {state.max_steps}\n\n"
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
