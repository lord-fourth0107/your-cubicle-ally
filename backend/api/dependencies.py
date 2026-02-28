"""
api/dependencies.py
------------------
Shared instances for the multi-agent workflow.
Used for scripts/play.py or other non-FastAPI entry points.

NOTE: The FastAPI app uses main.py lifespan + api.deps for DI instead.
"""

from pathlib import Path

from core.session_manager import SessionManager
from core.orchestrator import Orchestrator
from agents.coach_agent import CoachAgent
from agents.guardrail_agent import GuardrailAgent
from utilities.prompt_builder import PromptBuilder
from utilities.module_loader import ModuleLoader
from skills.skill_registry import SkillRegistry

# Skill registry — load definitions at import
_skill_registry = SkillRegistry()
_definitions_dir = Path(__file__).resolve().parent.parent / "skills" / "definitions"
if _definitions_dir.exists():
    _skill_registry.load_all(_definitions_dir)

# Module loader
_module_loader = ModuleLoader()

# Shared instances (must match main.py lifespan setup)
session_manager = SessionManager()
prompt_builder = PromptBuilder(
    skill_registry=_skill_registry,
    module_loader=_module_loader,
)
guardrail = GuardrailAgent()
orchestrator = Orchestrator(
    session_manager=session_manager,
    prompt_builder=prompt_builder,
    guardrail=guardrail,
)
coach_agent = CoachAgent()
