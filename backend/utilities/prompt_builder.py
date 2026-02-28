"""
utilities/prompt_builder.py
---------------------------
Assembles the full system prompt for any agent by composing:
  - the agent's base prompt template
  - skill injections (from the actor's assigned skills)
  - current scenario context (goal, setup, actor role/personality)
  - memory / turn history

This is the core of the skill system — skills are prompt_injections
that get woven into the actor's system prompt here.

Owner: Utilities team
Depends on: skills/skill_registry, core/game_state
Depended on by: all agent classes
"""

from ..skills.skill_registry import SkillRegistry
from ..core.game_state import ActorInstance


class PromptBuilder:
    def __init__(self, skill_registry: SkillRegistry):
        self.registry = skill_registry

    def build_actor_prompt(self, actor: ActorInstance, scenario_context: dict) -> str:
        """
        Build the full system prompt for an Actor Agent.

        Structure:
          [PERSONA]         — who the actor is
          [ROLE]            — their function in this scenario
          [PERSONALITY]     — how they behave in this scenario
          [SKILLS]          — injected prompt fragments from each skill
          [DIRECTIVE]       — what the Scenario Agent needs from them this turn
          [SCENARIO CONTEXT]— goal and setup, for grounding

        Skill injection strategy: skills are appended after personality,
        each clearly delimited so they can be debugged independently.

        TODO: implement prompt assembly logic.
        """
        raise NotImplementedError

    def build_evaluator_prompt(self, scenario_context: dict, turn_history: list) -> str:
        """
        Build the system prompt for the Evaluator Agent.

        Includes: goal, setup, rubric, few-shot examples, turn history.

        TODO: implement prompt assembly logic.
        """
        raise NotImplementedError

    def build_scenario_prompt(self, scenario_context: dict, turn_history: list) -> str:
        """
        Build the system prompt for the Scenario Agent.

        Includes: goal, setup, all actor roles/personalities, turn history,
        current step (for valence calibration of choices).

        TODO: implement prompt assembly logic.
        """
        raise NotImplementedError
