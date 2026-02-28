"""
agents/coach_agent.py
---------------------
Writes the end-of-scenario debrief. Runs once per session.
Uses the Gemini SDK (google-genai) with JSON response mode.

Output contract:
  {
    outcome: "won" | "lost",
    overall_score: int,
    summary: str,
    turn_breakdowns: [
      {
        step: int,
        player_choice: str,
        what_happened: str,
        compliance_insight: str,
        hp_delta: int
      }
    ],
    key_concepts: list[str],
    recommended_followup: list[str]
  }

Owner: Agents team
Depends on: core/game_state
Depended on by: API routes (debrief endpoint)
"""

import os
import json
from google import genai
from google.genai import types

from core.game_state import GameState


COACH_SYSTEM_PROMPT = """
You are a compassionate compliance coach delivering a post-scenario debrief.
Your job is to help the learner understand what they did well and where they
can improve. Be specific, constructive, and grounded in actual compliance
principles. Never be preachy or condescending.
""".strip()


class CoachAgent:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    async def debrief(self, state: GameState) -> dict:
        """
        Review the full GameState and produce a structured debrief.
        The reasoning field from each Evaluation drives the per-turn insights.
        """
        turn_summaries = "\n".join([
            f"Step {t.step}: Player chose \"{t.player_choice}\" | "
            f"HP delta: {t.hp_delta} | "
            f"Reasoning: {t.evaluation.reasoning if t.evaluation else 'N/A'}"
            for t in state.history
        ])

        prompt = (
            f"Scenario outcome: {state.status.value}\n"
            f"Player: {state.player_profile.role}, {state.player_profile.seniority}\n"
            f"Final HP: {state.player_hp} / 100\n\n"
            f"Turn history:\n{turn_summaries}\n\n"
            "Return a JSON object with exactly these fields:\n"
            "  outcome (str: 'won' or 'lost')\n"
            "  overall_score (int 0-100)\n"
            "  summary (str: 2-3 sentence overall assessment)\n"
            "  turn_breakdowns (list of objects: { step, player_choice, what_happened, compliance_insight, hp_delta })\n"
            "  key_concepts (list of str: compliance concepts this scenario covered)\n"
            "  recommended_followup (list of str: module ids worth trying next, can be empty)"
        )

        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=COACH_SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
        )

        return json.loads(response.text)
