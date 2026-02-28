"""
api/dependencies.py
------------------
Shared instances for the multi-agent workflow.
"""

from pathlib import Path

from core.session_manager import SessionManager
from core.orchestrator import Orchestrator
from agents.coach_agent import CoachAgent
from utilities.prompt_builder import PromptBuilder
from skills.skill_registry import SkillRegistry

# Skill registry — load definitions at import
_skill_registry = SkillRegistry()
_definitions_dir = Path(__file__).resolve().parent.parent / "skills" / "definitions"
if _definitions_dir.exists():
    _skill_registry.load_all(_definitions_dir)

# Shared instances
session_manager = SessionManager()
prompt_builder = PromptBuilder(_skill_registry)
orchestrator = Orchestrator(session_manager=session_manager, prompt_builder=prompt_builder)
coach_agent = CoachAgent()
