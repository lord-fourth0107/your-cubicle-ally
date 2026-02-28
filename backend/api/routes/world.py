"""
api/routes/world.py
-------------------
Endpoints for generative world setup — sprites and environment art.
Uses Google Gemini/Imagen to create a simulated environment for the arena.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from services.sprite_generator import (
    generate_actor_animation_frames,
    generate_actor_sprite,
    generate_environment_animation_frames,
    generate_environment_image,
    get_scenario_setting,
)

router = APIRouter()


class WorldGenerateRequest(BaseModel):
    module_id: str
    scenario_id: str | None = None
    scenario_setting: str | None = None
    actors: list[dict]  # [{ actor_id, name, role }]


class WorldGenerateResponse(BaseModel):
    environment_image: str | None  # base64 data URL
    actor_sprites: dict[str, str | None]  # actor_id -> single frame (for compatibility)
    actor_animations: dict[str, list[str]]  # actor_id -> [frame0, frame1, ...]
    environment_frames: list[str]  # [frame0, frame1] for animated background


@router.post("/generate", response_model=WorldGenerateResponse)
async def generate_world(body: WorldGenerateRequest):
    """
    Generate animated environment and character sprites using Gemini.
    Caches to disk — same scenario reuses cached animations on return.
    """
    key = body.scenario_id or body.module_id
    scenario_id = body.scenario_id or body.module_id
    setting = body.scenario_setting or get_scenario_setting(key)

    # Animated environment (2 frames for crossfade)
    env_frames = generate_environment_animation_frames(
        body.module_id, setting, scenario_id
    )
    environment_image = env_frames[0] if env_frames else generate_environment_image(
        body.module_id, setting
    )

    actor_sprites = {}
    actor_animations = {}
    for actor in body.actors:
        actor_id = actor.get("actor_id", "")
        name = actor.get("name", "Character")
        role = actor.get("role", "")
        frames = generate_actor_animation_frames(actor_id, name, role, scenario_id)
        if frames:
            actor_animations[actor_id] = frames
            actor_sprites[actor_id] = frames[0]
        else:
            sprite = generate_actor_sprite(actor_id, name, role)
            actor_sprites[actor_id] = sprite
            if sprite:
                actor_animations[actor_id] = [sprite]

    return WorldGenerateResponse(
        environment_image=environment_image,
        actor_sprites=actor_sprites,
        actor_animations=actor_animations,
        environment_frames=env_frames,
    )
