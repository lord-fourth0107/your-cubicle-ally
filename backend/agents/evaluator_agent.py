"""
agents/evaluator_agent.py
-------------------------
Judges the player's choice against the scenario goal, rubric,
and few-shot examples. Returns a structured Evaluation.

Uses the Gemini SDK directly with JSON response mode.

Output contract:
  {
    score: int (0–100),
    hp_delta: int (negative = damage, max penalty -40),
    reasoning: str (used by Coach Agent in debrief),
    is_critical_failure: bool
  }

Owner: Agents team
Depends on: core/game_state, utilities/prompt_builder
Depended on by: core/orchestrator
"""

import os
import json
import google.generativeai as genai
from core.game_state import GameState, Evaluation
from utilities.prompt_builder import PromptBuilder


class EvaluatorAgent:
    def __init__(self, prompt_builder: PromptBuilder):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel(
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        self.prompt_builder = prompt_builder

    async def evaluate(self, player_choice: str, state: GameState) -> Evaluation:
        """
        Evaluate the player's choice and return a structured Evaluation.

        Context passed to Gemini:
          - scenario goal, setup, actor roles/personalities
          - module rubric + few-shot evaluation examples
          - full turn history so far
          - current situation
          - player's choice

        JSON schema enforced via response_mime_type.
        """
        system_prompt = self.prompt_builder.build_evaluator_prompt(
            scenario_context=state.model_dump(),
            turn_history=state.history,
        )

        user_message = (
            f"The player responded: \"{player_choice}\"\n\n"
            "Return a JSON object with exactly these fields:\n"
            "  score (int 0-100)\n"
            "  hp_delta (int, negative means damage, max -40)\n"
            "  reasoning (str, 1-2 sentences explaining the score)\n"
            "  is_critical_failure (bool)"
        )

        response = await self.model.generate_content_async(
            [system_prompt, user_message]
        )

        data = json.loads(response.text)
        return Evaluation(**data)
