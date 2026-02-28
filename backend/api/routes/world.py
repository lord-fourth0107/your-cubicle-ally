"""
api/routes/world.py
-------------------
Endpoints for generative world setup — sprites and environment art.
Uses Google Gemini/Imagen to create a simulated environment for the arena.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from services.sprite_generator import (
    generate_actor_sprite,
    generate_environment_image,
    get_scenario_setting,
)

router = APIRouter()


class WorldGenerateRequest(BaseModel):
    module_id: str
    scenario_setting: str | None = None
    actors: list[dict]  # [{ actor_id, name, role }]


class WorldGenerateResponse(BaseModel):
    environment_image: str | None  # base64 data URL
    actor_sprites: dict[str, str | None]  # actor_id -> base64 data URL or None


@router.post("/generate", response_model=WorldGenerateResponse)
async def generate_world(body: WorldGenerateRequest):
    """
    Generate a simulated environment with sprites for the scenario.
    Called when the player enters the arena after selecting a module.

    Returns environment background + character sprites (base64 data URLs).
    If Imagen is unavailable, returns nulls — frontend falls back to placeholders.
    """
    setting = body.scenario_setting or get_scenario_setting(body.module_id)
    environment_image = generate_environment_image(body.module_id, setting)

    actor_sprites = {}
    for actor in body.actors:
        actor_id = actor.get("actor_id", "")
        name = actor.get("name", "Character")
        role = actor.get("role", "")
        sprite = generate_actor_sprite(actor_id, name, role)
        actor_sprites[actor_id] = sprite

    return WorldGenerateResponse(
        environment_image=environment_image,
        actor_sprites=actor_sprites,
    )
