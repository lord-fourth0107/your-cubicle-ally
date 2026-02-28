"""
core/game_state.py
------------------
Pydantic models that define the full game state shape.
This is the single source of truth for a session — every agent
reads from and writes to these models.

Owner: Core team
Depends on: nothing (pure data models)
Depended on by: session_manager, all agents, all API routes
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class SessionStatus(str, Enum):
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    COMPLETE = "complete"


class Choice(BaseModel):
    label: str
    valence: str  # "positive" | "neutral" | "negative"


class Evaluation(BaseModel):
    score: int               # 0–100
    hp_delta: int            # negative = damage
    reasoning: str           # used by Coach Agent in debrief
    is_critical_failure: bool


class ActorReaction(BaseModel):
    actor_id: str
    dialogue: str


class Turn(BaseModel):
    step: int
    situation: str
    turn_order: list[str]                        # actor_ids in order
    directives: dict[str, str]                   # actor_id → directive
    actor_reactions: list[ActorReaction]
    choices_offered: list[Choice]
    player_choice: str
    evaluation: Optional[Evaluation] = None
    hp_delta: int = 0
    narrative_branch: str = ""


class Message(BaseModel):
    role: str    # "system" | "user" | "assistant"
    content: str


class ActorInstance(BaseModel):
    actor_id: str
    persona: str                    # base system prompt / character definition
    role: str                       # role in this specific scenario
    personality: str                # personality traits for this scenario
    skills: list[str]               # skill ids
    tools: list[str]                # tool ids
    memory: list[Message] = []      # rolling conversation history
    current_directive: str = ""     # set by Scenario Agent each turn


class PlayerProfile(BaseModel):
    role: str
    seniority: str
    domain: str
    raw_context: str                # full resume/JD text


class GameState(BaseModel):
    session_id: str
    player_profile: PlayerProfile
    module_id: str
    scenario_id: str
    actors: list[ActorInstance]
    current_step: int = 0
    max_steps: int = 6
    player_hp: int = 100
    history: list[Turn] = []
    status: SessionStatus = SessionStatus.ACTIVE
