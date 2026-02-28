"""
core/orchestrator.py
--------------------
Coordinates all agent calls for a single turn.
This is the main entry point for turn processing.

Turn sequence:
  0. GuardrailAgent  — validates player input (rule-based + LLM for free-write)
  1. Evaluator Agent — judges player choice, returns hp_delta + reasoning
     → GuardrailAgent clamps evaluator output to valid bounds
  2. Scenario Agent  — determines turn order, directives, narrative branch, next choices
     → GuardrailAgent validates scenario structure
  3. Actor Agents    — react in character per their directive (sequential per turn_order)
     → GuardrailAgent fixes actor dialogue format
  4. Session Manager — applies the completed Turn to GameState (persists to SQLite)

Actor Agents are long-lived — one ActorAgent instance per actor per session,
stored in actor_agents dict. This keeps the Chat alive across turns so each
actor has genuine memory continuity.

Owner: Core team
Depends on: all agents, session_manager, game_state
Depended on by: API routes
"""

from .game_state import GameState, SessionStatus, Turn
from .session_manager import SessionManager
from ..agents.evaluator_agent import EvaluatorAgent
from ..agents.scenario_agent import ScenarioAgent
from ..agents.actor_agent import ActorAgent
from ..agents.guardrail_agent import GuardrailAgent
from ..utilities.prompt_builder import PromptBuilder


class Orchestrator:
    def __init__(
        self,
        session_manager: SessionManager,
        prompt_builder: PromptBuilder,
        guardrail: GuardrailAgent,
    ):
        self.session_manager = session_manager
        self.prompt_builder = prompt_builder
        self.guardrail = guardrail
        self.evaluator = EvaluatorAgent(prompt_builder=prompt_builder)
        self.scenario = ScenarioAgent(prompt_builder=prompt_builder)
        # Keyed by session_id → { actor_id → ActorAgent }
        # Keeps Chat alive across all turns for each actor
        self._actor_agents: dict[str, dict[str, ActorAgent]] = {}

    def _get_or_create_actor_agents(
        self, session_id: str, state: GameState
    ) -> dict[str, ActorAgent]:
        """Return persistent ActorAgent instances for this session, creating them if needed."""
        if session_id not in self._actor_agents:
            scenario_context = state.model_dump()
            self._actor_agents[session_id] = {
                actor.actor_id: ActorAgent(
                    actor=actor,
                    prompt_builder=self.prompt_builder,
                    scenario_context=scenario_context,
                )
                for actor in state.actors
            }
        return self._actor_agents[session_id]

    def cleanup_session(self, session_id: str) -> None:
        """Drop actor agent instances when a session ends."""
        self._actor_agents.pop(session_id, None)

    def reset_actors(self, session_id: str) -> None:
        """
        Drop actor agents for a retry — they will be recreated on the next
        process_turn call with fresh Chat history.
        """
        self._actor_agents.pop(session_id, None)

    async def process_turn(self, session_id: str, player_choice: str) -> GameState:
        """
        Run a full turn cycle and return the updated GameState.
        Guardrail checks are interleaved at each stage.
        """
        state = self.session_manager.get(session_id)

        # Step 0: Guard player input — raises GuardrailViolation on failure
        await self.guardrail.validate_player_input(player_choice, state)

        actor_agents = self._get_or_create_actor_agents(session_id, state)

        # Step 1: Evaluate the player's choice
        evaluation = await self.evaluator.evaluate(
            player_choice=player_choice,
            state=state,
        )
        # Clamp evaluator output to the scenario's configured HP delta bounds
        evaluation = self.guardrail.fix_evaluator_output(evaluation, state.scoring)

        # Step 2: Scenario Agent decides turn order, directives, next situation + choices
        scenario_output = await self.scenario.advance(
            player_choice=player_choice,
            evaluation=evaluation,
            state=state,
        )
        # Validate scenario structure — raises ValueError on bad output
        valid_actor_ids = [a.actor_id for a in state.actors]
        self.guardrail.validate_scenario_output(scenario_output, valid_actor_ids)

        # Step 3: Actor Agents react in turn order
        actor_reactions = []
        for actor_id in scenario_output.turn_order:
            actor_instance = next(a for a in state.actors if a.actor_id == actor_id)
            actor_instance.current_directive = scenario_output.directives[actor_id]
            agent = actor_agents[actor_id]
            reaction = await agent.react(state=state)
            # Fix actor dialogue format (strip quotes, detect narration)
            reaction.dialogue = self.guardrail.fix_actor_dialogue(
                reaction.dialogue, actor_id
            )
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
            resolved_early=scenario_output.early_resolution and state.allow_early_resolution,
        )

        updated_state = self.session_manager.apply_turn(session_id, turn)

        # Drop in-memory actor agents once the session is no longer active
        if updated_state.status != SessionStatus.ACTIVE:
            self.cleanup_session(session_id)

        return updated_state
