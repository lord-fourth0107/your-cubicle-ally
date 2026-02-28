"""
agents/actor_agent.py
---------------------
A mini agent that plays a single character in the scenario.
Each actor has a persona, skills, tools, memory, and a current directive.

Uses the Gemini SDK (google-genai) with a persistent async Chat per actor.
The Chat carries conversation history automatically across turns.

Prompt structure:
  - STATIC (set once via system_instruction in the Chat config):
      persona, role, personality, skill injections, scenario goal + setup
  - DYNAMIC (sent as user message each turn):
      current situation + directive for this turn

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
from google import genai
from google.genai import types
from ..core.game_state import ActorInstance, ActorReaction, GameState, Message
from ..utilities.prompt_builder import PromptBuilder


class ActorAgent:
    def __init__(self, actor: ActorInstance, prompt_builder: PromptBuilder, scenario_context: dict):
        self.actor = actor
        self.prompt_builder = prompt_builder

        # Static system prompt — built once at session start.
        # Contains: persona, role, personality, skill injections, scenario goal + setup.
        # The directive and situation are NOT here — they change every turn.
        static_system_prompt = prompt_builder.build_actor_system_prompt(
            actor=actor,
            scenario_context=scenario_context,
        )

        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

        # Convert existing memory to SDK Content objects (used when resuming after retry)
        history = [
            types.Content(
                role=msg.role if msg.role != "assistant" else "model",
                parts=[types.Part(text=msg.content)],
            )
            for msg in actor.memory
        ]

        self.chat = self.client.aio.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=static_system_prompt,
            ),
            history=history,
        )

    async def react(self, state: GameState) -> ActorReaction:
        """
        Generate an in-character reaction for this turn.

        Only the dynamic parts are sent as the user message:
          - current situation (what's happening right now)
          - current directive (what the Scenario Agent needs this turn)

        The Chat automatically carries all prior dialogue forward.
        Memory is updated here after each turn.
        """
        current_situation = (
            state.history[-1].situation if state.history else "The scenario is just beginning."
        )

        user_message = (
            f"Situation: {current_situation}\n"
            f"Your directive: {self.actor.current_directive}\n\n"
            "Respond in character. One to three sentences only."
        )

        response = await self.chat.send_message(user_message)
        dialogue = response.text.strip()

        # Sync actor's memory on the ActorInstance (used if session is serialised or retried)
        self.actor.memory.append(Message(role="user", content=current_situation))
        self.actor.memory.append(Message(role="model", content=dialogue))

        return ActorReaction(actor_id=self.actor.actor_id, dialogue=dialogue)
