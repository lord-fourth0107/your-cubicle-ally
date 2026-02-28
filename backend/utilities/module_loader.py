"""
utilities/module_loader.py
--------------------------
Loads scenario YAML files from the modules/ directory and parses them
into typed ScenarioData models.

Scenarios are cached after first load so the same YAML is not re-read
on every turn.

Owner: Utilities team
Depends on: pyyaml, pydantic
Depended on by: session_initializer, prompt_builder
"""

import yaml
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel


MODULES_DIR = Path(__file__).parent.parent / "modules"


# ---------------------------------------------------------------------------
# Typed schema for scenario YAML files
# ---------------------------------------------------------------------------

class FewShotExample(BaseModel):
    choice: str
    score: int
    reasoning: str


class Rubric(BaseModel):
    goal: str
    key_concepts: list[str]
    few_shot_examples: list[FewShotExample]


class EntryActorReaction(BaseModel):
    actor_id: str
    dialogue: str


class EntryChoiceData(BaseModel):
    label: str
    valence: str  # "positive" | "neutral" | "negative"


class EntryTurnData(BaseModel):
    situation: str
    turn_order: list[str]
    directives: dict[str, str]
    actor_reactions: list[EntryActorReaction]
    choices_offered: list[EntryChoiceData]


class ActorData(BaseModel):
    actor_id: str
    persona: str
    role: str
    personality: str
    skills: list[str]
    tools: list[str] = []


class ScenarioData(BaseModel):
    id: str
    module_id: str
    title: str
    max_steps: int
    rubric: Rubric
    entry_turn: EntryTurnData
    actors: list[ActorData]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class ModuleLoader:
    """Loads and caches scenario YAML files."""

    def __init__(self, modules_dir: Path = MODULES_DIR):
        self._modules_dir = modules_dir
        self._cache: dict[str, ScenarioData] = {}

    def load_scenario(self, module_id: str, scenario_id: str) -> ScenarioData:
        """
        Load a scenario by module_id and scenario_id.
        Raises FileNotFoundError if the YAML does not exist.
        Results are cached after first load.
        """
        cache_key = f"{module_id}/{scenario_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self._modules_dir / module_id / "scenarios" / f"{scenario_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(
                f"Scenario YAML not found: {path}. "
                f"Check that module_id={module_id!r} and scenario_id={scenario_id!r} are correct."
            )

        with open(path) as f:
            raw = yaml.safe_load(f)

        scenario = ScenarioData(**raw)
        self._cache[cache_key] = scenario
        return scenario

    def list_scenarios(self, module_id: str) -> list[str]:
        """Return all scenario IDs available for a given module."""
        module_dir = self._modules_dir / module_id / "scenarios"
        if not module_dir.exists():
            return []
        return [p.stem for p in module_dir.glob("*.yaml")]
