"""
utilities/session_initializer.py
---------------------------------
Creates a fresh GameState from a scenario YAML definition and a player profile.
Called once per session at /session/start.

Owner: Utilities team
Depends on: module_loader, core/game_state
Depended on by: api/routes/session
"""

import uuid
from ..core.game_state import (
    GameState,
    SessionStatus,
    ActorInstance,
    PlayerProfile,
    Turn,
    Choice,
    ActorReaction,
)
from .module_loader import ModuleLoader


class SessionInitializer:
    def __init__(self, module_loader: ModuleLoader):
        self.loader = module_loader

    def create_session(
        self,
        player_profile: PlayerProfile,
        module_id: str,
        scenario_id: str,
    ) -> GameState:
        """
        Load the scenario YAML and build a fresh GameState for a new session.
        The entry turn (step 0) is pre-populated with the scenario's opening
        situation and first set of player choices.
        """
        scenario = self.loader.load_scenario(module_id, scenario_id)
        session_id = str(uuid.uuid4())

        actors = [
            ActorInstance(
                actor_id=a.actor_id,
                persona=a.persona,
                role=a.role,
                personality=a.personality,
                skills=a.skills,
                tools=a.tools,
                memory=[],
                current_directive="",
            )
            for a in scenario.actors
        ]

        entry = scenario.entry_turn
        entry_turn = Turn(
            step=0,
            situation=entry.situation,
            turn_order=entry.turn_order,
            directives=entry.directives,
            actor_reactions=[
                ActorReaction(actor_id=r.actor_id, dialogue=r.dialogue)
                for r in entry.actor_reactions
            ],
            choices_offered=[
                Choice(label=c.label, valence=c.valence)
                for c in entry.choices_offered
            ],
            player_choice="",
            evaluation=None,
            hp_delta=0,
            narrative_branch="entry",
        )

        return GameState(
            session_id=session_id,
            player_profile=player_profile,
            module_id=module_id,
            scenario_id=scenario_id,
            actors=actors,
            current_step=0,
            max_steps=scenario.max_steps,
            starting_hp=scenario.starting_hp,
            player_hp=scenario.starting_hp,
            scoring=scenario.scoring,
            allow_early_resolution=scenario.allow_early_resolution,
            history=[entry_turn],
            status=SessionStatus.ACTIVE,
        )
