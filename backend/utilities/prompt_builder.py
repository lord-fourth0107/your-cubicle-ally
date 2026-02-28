"""
utilities/prompt_builder.py
---------------------------
Assembles prompts for all agents.

Actor prompts are split into two parts:
  - build_actor_system_prompt() — STATIC, set once as system_instruction at actor init.
      Contains: persona, role, personality, skill injections, scenario goal + setup.
  - Dynamic turn message — NOT built here. ActorAgent constructs it inline:
      "Situation: ...\nYour directive: ..."

All other agents (Evaluator, Scenario, Coach) use single-call prompts
assembled by their respective build_*_prompt() methods.

Skill injection strategy (decided):
  Skills are appended after personality, each clearly delimited.

Owner: Utilities team
Depends on: skills/skill_registry, core/game_state
Depended on by: all agent classes
"""

from ..skills.skill_registry import SkillRegistry
from ..core.game_state import ActorInstance


class PromptBuilder:
    def __init__(self, skill_registry: SkillRegistry):
        self.registry = skill_registry

    def build_actor_system_prompt(self, actor: ActorInstance, scenario_context: dict) -> str:
        """
        Build the STATIC system prompt for an Actor Agent.
        Called once at session start, set as system_instruction on the GenerativeModel.

        Structure:
          [PERSONA]           — who the actor is
          [ROLE]              — their function in this scenario
          [PERSONALITY]       — how they behave in this scenario
          [SKILLS]            — injected prompt fragments from each assigned skill,
                                each clearly delimited for debuggability
          [SCENARIO CONTEXT]  — scenario goal + setup, so the actor is grounded
                                in the situation from turn one

        Skills are appended after personality, each wrapped in a clear delimiter.
        The directive and current situation are NOT here — they change every turn
        and are passed as the user message in ActorAgent.react().

        TODO: implement prompt assembly logic.
        """
        raise NotImplementedError

    def build_evaluator_prompt(self, scenario_context: dict, turn_history: list) -> str:
        """
        Build the system prompt for the Evaluator Agent.

        Includes: scenario goal, setup, actor roster, module rubric,
        few-shot evaluation examples, full turn history.

        TODO: implement prompt assembly logic.
        """
        raise NotImplementedError

    def build_scenario_prompt(self, scenario_context: dict, turn_history: list) -> str:
        """
        Build the system prompt for the Scenario Agent.

        Includes: scenario goal, setup, all actor roles/personalities,
        full turn history, current step number (for choice valence calibration).

        TODO: implement prompt assembly logic.
        """
        raise NotImplementedError
