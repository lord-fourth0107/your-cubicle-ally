"""
core/orchestrator.py
--------------------
Coordinates all agent calls for a single turn.
This is the main entry point for turn processing.

Turn sequence:
  1. Evaluator Agent   — judges player choice, returns hp_delta + reasoning
  2. Scenario Agent    — determines turn order, directives, narrative branch, next choices
  3. Actor Agents      — react in character per their directive (parallel where possible)
  4. Session Manager   — applies the completed Turn to GameState

Owner: Core team
Depends on: all agents, session_manager, game_state
Depended on by: API routes
"""

from .game_state import GameState, Turn
from .session_manager import SessionManager
from ..agents.evaluator_agent import EvaluatorAgent
from ..agents.scenario_agent import ScenarioAgent
from ..agents.actor_agent import ActorAgent


class Orchestrator:
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.evaluator = EvaluatorAgent()
        self.scenario = ScenarioAgent()

    async def process_turn(self, session_id: str, player_choice: str) -> GameState:
        """
        Run a full turn cycle and return the updated GameState.
        """
        state = self.session_manager.get(session_id)

        # Step 1: Evaluate the player's choice
        evaluation = await self.evaluator.evaluate(
            player_choice=player_choice,
            state=state,
        )

        # Step 2: Scenario Agent decides turn order, directives, next situation + choices
        scenario_output = await self.scenario.advance(
            player_choice=player_choice,
            evaluation=evaluation,
            state=state,
        )

        # Step 3: Actor Agents react in turn order
        actor_reactions = []
        for actor_id in scenario_output.turn_order:
            actor_instance = next(a for a in state.actors if a.actor_id == actor_id)
            actor_instance.current_directive = scenario_output.directives[actor_id]
            agent = ActorAgent(actor_instance)
            reaction = await agent.react(state=state)
            actor_instance.memory.append({"role": "assistant", "content": reaction.dialogue})
            actor_reactions.append(reaction)

        # Step 4: Assemble the Turn and apply to session
        turn = Turn(
            step=state.current_step,
            situation=scenario_output.situation_summary,
            turn_order=scenario_output.turn_order,
            directives=scenario_output.directives,
            actor_reactions=actor_reactions,
            choices_offered=scenario_output.next_choices,
            player_choice=player_choice,
            evaluation=evaluation,
            hp_delta=evaluation.hp_delta,
            narrative_branch=scenario_output.branch_taken,
        )

        return self.session_manager.apply_turn(session_id, turn)
