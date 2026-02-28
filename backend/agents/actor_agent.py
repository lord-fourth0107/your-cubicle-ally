"""
agents/actor_agent.py
---------------------
A mini agent that plays a single character in the scenario.
Each actor has a persona, skills, tools, memory, and a current directive.

Uses the Gemini SDK directly with a multi-turn chat session.
Actor memory is maintained as a Gemini ChatSession — each ActorAgent
holds its own session so conversation history persists across turns.

The actor ALWAYS responds in character. The directive shapes intent, not voice.

Output contract:
  {
    actor_id: str,
    dialogue: str    # the actor's in-character response this turn
  }

Owner: Agents team
Depends on: core/game_state, utilities/prompt_builder
Depended on by: core/orchestrator
"""

import os
import google.generativeai as genai
from google.generativeai.types import ContentDict
from ..core.game_state import ActorInstance, ActorReaction, GameState
from ..utilities.prompt_builder import PromptBuilder


class ActorAgent:
    def __init__(self, actor: ActorInstance, prompt_builder: PromptBuilder):
        self.actor = actor
        self.prompt_builder = prompt_builder

        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel(
            model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        )

        # Gemini ChatSession maintains the conversation history automatically.
        # Seed it with any existing memory from the ActorInstance (e.g. on retry).
        history: list[ContentDict] = [
            {"role": msg.role, "parts": [msg.content]}
            for msg in actor.memory
        ]
        self.chat = self.model.start_chat(history=history)

    async def react(self, state: GameState) -> ActorReaction:
        """
        Generate an in-character reaction for this turn.

        The system prompt (assembled by PromptBuilder) contains:
          - persona, role, personality, skill injections
          - scenario goal + setup
          - current directive from the Scenario Agent

        The Gemini ChatSession carries forward the full conversation
        history automatically — no manual history management needed.
        """
        # Rebuild system prompt each turn so directive + scenario context are fresh
        system_prompt = self.prompt_builder.build_actor_prompt(
            actor=self.actor,
            scenario_context=state.model_dump(),
        )

        current_situation = (
            state.history[-1].situation if state.history else "The scenario is just beginning."
        )

        user_message = (
            f"{system_prompt}\n\n"
            f"Current situation: {current_situation}\n"
            f"Your directive this turn: {self.actor.current_directive}\n\n"
            "Respond in character. One to three sentences only."
        )

        response = await self.chat.send_message_async(user_message)
        dialogue = response.text.strip()

        # Keep ActorInstance.memory in sync (used for session persistence / debrief)
        self.actor.memory.append({"role": "user", "content": current_situation})
        self.actor.memory.append({"role": "model", "content": dialogue})

        return ActorReaction(actor_id=self.actor.actor_id, dialogue=dialogue)
