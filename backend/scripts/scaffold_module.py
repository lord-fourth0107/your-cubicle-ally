#!/usr/bin/env python3
"""
Generate backend module scenario YAML files from a filled blueprint submission.

Usage:
  python backend/scripts/scaffold_module.py --submission path/to/submission.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.game_state import ScoringConfig
from utilities.module_loader import ModuleLoader


DEFAULT_MODULES_DIR = ROOT / "backend" / "modules"


class FewShotExampleSubmission(BaseModel):
    choice: str
    score: int
    reasoning: str


class RubricSubmission(BaseModel):
    goal: str
    key_concepts: list[str]
    few_shot_examples: list[FewShotExampleSubmission]


class EntryActorReactionSubmission(BaseModel):
    actor_id: str
    dialogue: str


class EntryChoiceSubmission(BaseModel):
    label: str
    valence: Literal["positive", "neutral", "negative"]


class EntryTurnSubmission(BaseModel):
    situation: str
    turn_order: list[str]
    directives: dict[str, str]
    actor_reactions: list[EntryActorReactionSubmission]
    choices_offered: list[EntryChoiceSubmission]


class ActorSubmission(BaseModel):
    actor_id: str
    persona: str
    role: str
    personality: str
    skills: list[str]
    tools: list[str] = []


class ScenarioSubmission(BaseModel):
    id: str
    title: str
    max_steps: int = 10
    starting_hp: int = 100
    allow_early_resolution: bool = True
    scoring: ScoringConfig | None = None
    rubric: RubricSubmission
    entry_turn: EntryTurnSubmission
    actors: list[ActorSubmission]

    @model_validator(mode="after")
    def validate_actor_references(self) -> "ScenarioSubmission":
        actor_ids = {a.actor_id for a in self.actors}
        if len(actor_ids) != len(self.actors):
            raise ValueError(f"Scenario {self.id!r} has duplicate actor_ids.")

        missing_in_turn_order = [a for a in self.entry_turn.turn_order if a not in actor_ids]
        if missing_in_turn_order:
            raise ValueError(
                f"Scenario {self.id!r} turn_order references unknown actor_ids: {missing_in_turn_order}"
            )

        missing_in_directives = [a for a in self.entry_turn.directives if a not in actor_ids]
        if missing_in_directives:
            raise ValueError(
                f"Scenario {self.id!r} directives reference unknown actor_ids: {missing_in_directives}"
            )

        missing_in_reactions = [
            r.actor_id for r in self.entry_turn.actor_reactions if r.actor_id not in actor_ids
        ]
        if missing_in_reactions:
            raise ValueError(
                f"Scenario {self.id!r} actor_reactions reference unknown actor_ids: "
                f"{missing_in_reactions}"
            )

        return self


class ModuleMetaSubmission(BaseModel):
    id: str
    name: str
    description: str
    version: str = "1.0"


class ModuleSubmission(BaseModel):
    module: ModuleMetaSubmission
    scenarios: list[ScenarioSubmission] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scenario_ids(self) -> "ModuleSubmission":
        ids = [s.id for s in self.scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate scenario IDs found in submission.")
        return self


def _scenario_to_yaml_dict(module_id: str, scenario: ScenarioSubmission) -> dict:
    out = {
        "id": scenario.id,
        "module_id": module_id,
        "title": scenario.title,
        "max_steps": scenario.max_steps,
        "starting_hp": scenario.starting_hp,
        "allow_early_resolution": scenario.allow_early_resolution,
        "rubric": {
            "goal": scenario.rubric.goal,
            "key_concepts": scenario.rubric.key_concepts,
            "few_shot_examples": [
                {"choice": e.choice, "score": e.score, "reasoning": e.reasoning}
                for e in scenario.rubric.few_shot_examples
            ],
        },
        "entry_turn": {
            "situation": scenario.entry_turn.situation,
            "turn_order": scenario.entry_turn.turn_order,
            "directives": scenario.entry_turn.directives,
            "actor_reactions": [
                {"actor_id": r.actor_id, "dialogue": r.dialogue}
                for r in scenario.entry_turn.actor_reactions
            ],
            "choices_offered": [
                {"label": c.label, "valence": c.valence}
                for c in scenario.entry_turn.choices_offered
            ],
        },
        "actors": [
            {
                "actor_id": a.actor_id,
                "persona": a.persona,
                "role": a.role,
                "personality": a.personality,
                "skills": a.skills,
                "tools": a.tools,
            }
            for a in scenario.actors
        ],
    }

    if scenario.scoring is not None:
        out["scoring"] = scenario.scoring.model_dump()

    return out


def load_submission(path: Path) -> ModuleSubmission:
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return ModuleSubmission(**raw)


def write_module(
    submission: ModuleSubmission,
    modules_dir: Path,
    force: bool,
) -> list[Path]:
    module_id = submission.module.id
    module_dir = modules_dir / module_id
    scenarios_dir = module_dir / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for scenario in submission.scenarios:
        out_path = scenarios_dir / f"{scenario.id}.yaml"
        if out_path.exists() and not force:
            raise FileExistsError(f"Refusing to overwrite existing file: {out_path}")
        payload = _scenario_to_yaml_dict(module_id, scenario)
        with out_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=False)
        written.append(out_path)

    module_meta_path = module_dir / "module.meta.yaml"
    if (not module_meta_path.exists()) or force:
        with module_meta_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(submission.module.model_dump(), f, sort_keys=False, allow_unicode=False)
        written.append(module_meta_path)

    return written


def validate_written_module(modules_dir: Path, submission: ModuleSubmission) -> None:
    loader = ModuleLoader(modules_dir=modules_dir)
    module_id = submission.module.id
    for scenario in submission.scenarios:
        loader.load_scenario(module_id, scenario.id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold backend module scenarios from template.")
    parser.add_argument("--submission", type=Path, required=True, help="Filled submission YAML file.")
    parser.add_argument(
        "--modules-dir",
        type=Path,
        default=DEFAULT_MODULES_DIR,
        help="Target modules directory (default: backend/modules).",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated files.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print actions only.")
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip post-write schema validation via ModuleLoader.",
    )
    args = parser.parse_args()

    try:
        submission = load_submission(args.submission)
    except FileNotFoundError:
        print(f"Submission file not found: {args.submission}")
        return 1
    except ValidationError as e:
        print("Submission validation failed:")
        print(e)
        return 1
    except Exception as e:
        print(f"Could not parse submission: {e}")
        return 1

    module_id = submission.module.id
    target_dir = args.modules_dir / module_id / "scenarios"
    planned = [target_dir / f"{s.id}.yaml" for s in submission.scenarios]

    if args.dry_run:
        print("Dry run successful.")
        print(f"Module: {module_id}")
        for p in planned:
            print(f"Would write: {p}")
        print(f"Would write: {args.modules_dir / module_id / 'module.meta.yaml'}")
        return 0

    try:
        written = write_module(submission=submission, modules_dir=args.modules_dir, force=args.force)
        if not args.skip_validate:
            validate_written_module(args.modules_dir, submission)
    except Exception as e:
        print(f"Generation failed: {e}")
        return 1

    print("Module scaffolding complete.")
    for p in written:
        print(f"Wrote: {p}")
    if not args.skip_validate:
        print("Validation: OK (ModuleLoader loaded generated scenarios).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
