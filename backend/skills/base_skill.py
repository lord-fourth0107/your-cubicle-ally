"""
skills/base_skill.py
--------------------
Pydantic model for a skill definition.
Skills are loaded from YAML files in skills/definitions/.

Each skill is a reusable behavioral bundle that can be
attached to any Actor Agent. Skills shape how an actor behaves
without changing who they are (that's the persona's job).

Owner: Skills team
Depends on: nothing
Depended on by: skill_registry, prompt_builder
"""

from pydantic import BaseModel


class Skill(BaseModel):
    id: str
    name: str
    description: str
    prompt_injection: str       # text injected into the actor's system prompt
    grants_tools: list[str]     # tool ids this skill unlocks for the actor
    conflicts_with: list[str]   # skill ids that cannot be used alongside this one
