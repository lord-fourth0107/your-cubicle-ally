"""
skills/skill_registry.py
------------------------
Loads all skill YAML definitions from skills/definitions/ at startup
and provides lookup by skill id.

Owner: Skills team
Depends on: base_skill
Depended on by: prompt_builder, session_initializer
"""

import yaml
from pathlib import Path
from .base_skill import Skill


class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def load_all(self, definitions_dir: Path = Path(__file__).parent / "definitions") -> None:
        """Load all .yaml files in the definitions directory."""
        for path in definitions_dir.glob("*.yaml"):
            with open(path) as f:
                data = yaml.safe_load(f)
            skill = Skill(**data)
            self._skills[skill.id] = skill

    def get(self, skill_id: str) -> Skill:
        """Retrieve a skill by id. Raises KeyError if not found."""
        return self._skills[skill_id]

    def get_many(self, skill_ids: list[str]) -> list[Skill]:
        """Retrieve multiple skills. Raises KeyError on any missing id."""
        return [self.get(sid) for sid in skill_ids]

    def validate_compatibility(self, skill_ids: list[str]) -> list[str]:
        """
        Check for conflicting skills in a list.
        Returns a list of conflict descriptions (empty = no conflicts).
        """
        conflicts = []
        skills = self.get_many(skill_ids)
        for skill in skills:
            for conflict_id in skill.conflicts_with:
                if conflict_id in skill_ids:
                    conflicts.append(f"{skill.id} conflicts with {conflict_id}")
        return conflicts
