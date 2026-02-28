"""
services/sprite_generator.py
----------------------------
Generates sprites and environment art using Google Gemini.
Uses gemini-2.0-flash-exp-image-generation (free tier) for native image gen.
Creates a simulated world for the compliance training arena.
Caches generated images to disk to avoid re-generation.
"""

import os
import base64
import io
import re
from pathlib import Path
from typing import List, Optional

_genai_client = None

# Cache directory: backend/cache/sprite_cache/ (created on first use)
_CACHE_DIR: Path | None = None


def _get_cache_dir() -> Path:
    """Get or create the sprite cache directory."""
    global _CACHE_DIR
    if _CACHE_DIR is not None:
        return _CACHE_DIR
    # This file is backend/services/sprite_generator.py → base = backend/
    base = Path(__file__).resolve().parent.parent
    _CACHE_DIR = base / "cache" / "sprite_cache"
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR


def _safe_filename(s: str) -> str:
    """Sanitize string for use in filenames."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", s)[:64]


def _cache_path(category: str, key: str, ext: str = ".png") -> Path:
    return _get_cache_dir() / f"{category}_{key}{ext}"


def _load_from_cache(path: Path) -> Optional[str]:
    """Load image from cache file, return base64 data URL or None."""
    try:
        if path.exists():
            data = path.read_bytes()
            return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except Exception:
        pass
    return None


def _save_to_cache(path: Path, data: bytes) -> None:
    """Save raw image bytes to cache."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    except Exception as e:
        print(f"[sprite_generator] Cache write failed: {e}")


def _get_genai_client():
    """Get Google GenAI client for Gemini image generation (free tier)."""
    global _genai_client
    if _genai_client is not None:
        return _genai_client
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        _genai_client = ("none", None)
        return _genai_client
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        _genai_client = ("genai", client, types)
        return _genai_client
    except ImportError:
        _genai_client = ("none", None)
        return _genai_client
    except Exception:
        _genai_client = ("none", None)
        return _genai_client




def _generate_image_gemini(client, types, prompt: str, aspect_hint: str = "16:9") -> Optional[bytes]:
    """Use Gemini 2.0 Flash native image generation (free tier)."""
    model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-exp-image-generation")
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    return part.inline_data.data
    except Exception as e:
        print(f"[sprite_generator] Gemini image gen failed: {e}")
    return None


def generate_environment_animation_frames(
    module_id: str, scenario_setting: str, scenario_id: str
) -> List[str]:
    """
    Generate 2 cached environment frames for subtle crossfade. Reused when returning.
    Returns list of base64 data URLs.
    """
    cache_key = f"{_safe_filename(scenario_id)}_{_safe_filename(module_id)}"
    frames = []
    for i in range(2):
        path = _cache_path("env_anim", f"{cache_key}_f{i}")
        cached = _load_from_cache(path)
        if cached:
            frames.append(cached)
    if len(frames) == 2:
        return frames

    client_info = _get_genai_client()
    if client_info[0] != "genai":
        return []

    model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-exp-image-generation")
    prompts = [
        f"Professional workplace illustration: {scenario_setting}. Soft isometric view, warm lighting. Frame 1: standard angle.",
        f"Same scene as before: {scenario_setting}. Slightly different camera angle or lighting. Consistent style. Frame 2.",
    ]
    _, client, types = client_info
    for i, prompt in enumerate(prompts):
        data = _generate_image_gemini(client, types, prompt)
        if data:
            path = _cache_path("env_anim", f"{cache_key}_f{i}")
            _save_to_cache(path, data)
            frames.append(f"data:image/png;base64,{base64.b64encode(data).decode()}")

    if len(frames) == 1:
        frames.append(frames[0])
    return frames[:2]


def generate_environment_image(module_id: str, scenario_setting: str) -> Optional[str]:
    """
    Generate an environment/setting image for the scenario.
    Returns base64 data URL or None on failure.
    Uses Gemini 2.0 Flash image generation (free tier).
    """
    cache_key = _safe_filename(module_id)
    cache_path = _cache_path("env", cache_key)
    cached = _load_from_cache(cache_path)
    if cached is not None:
        return cached

    client_info = _get_genai_client()
    if client_info[0] != "genai":
        return None

    _, client, types = client_info
    prompt = (
        f"Create a single professional workplace illustration: {scenario_setting}. "
        "Soft isometric or top-down view, warm lighting, clean vector illustration style, "
        "suitable for a corporate training simulation. Wide 16:9 composition. "
        "No text in the image."
    )
    data = _generate_image_gemini(client, types, prompt)
    if data:
        _save_to_cache(cache_path, data)
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    return None


def _generate_animation_frames_gemini(client, types, actor_id: str, name: str, role: str) -> List[bytes]:
    """Generate 4 animation frames in one request. Returns list of image bytes."""
    model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-exp-image-generation")
    prompt = (
        f"Generate exactly 4 frames of the same character for an idle animation. "
        f"Character: {name}, {role}. "
        "Frame 1: neutral expression, face camera. "
        "Frame 2: very slight nod, friendly acknowledgment. "
        "Frame 3: subtle head tilt to the side, listening. "
        "Frame 4: back to neutral, same as frame 1. "
        "Keep the SAME character, SAME clothing, SAME style in all 4 frames. "
        "Flat illustration style, circular avatar composition, workplace setting. "
        "Corporate training simulation. No text. Each frame square 1:1."
    )
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )
        frames = []
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                    frames.append(part.inline_data.data)
        return frames[:4]  # cap at 4
    except Exception as e:
        print(f"[sprite_generator] Animation frames failed: {e}")
        return []


def generate_actor_animation_frames(
    actor_id: str, name: str, role: str, scenario_id: str
) -> List[str]:
    """
    Generate 4 cached animation frames for an actor. Reused when returning to same scenario.
    Returns list of base64 data URLs, or empty if failed.
    """
    cache_key = f"{_safe_filename(scenario_id)}_{_safe_filename(actor_id)}"
    frames = []
    for i in range(4):
        path = _cache_path("anim", f"{cache_key}_f{i}")
        cached = _load_from_cache(path)
        if cached:
            frames.append(cached)
    if len(frames) == 4:
        return frames

    client_info = _get_genai_client()
    if client_info[0] != "genai":
        return []

    _, client, types = client_info
    raw_frames = _generate_animation_frames_gemini(client, types, actor_id, name, role)
    if len(raw_frames) < 2:
        # Fallback: use single sprite for all frames
        single = generate_actor_sprite(actor_id, name, role)
        if single:
            return [single] * 4
        return []

    for i, data in enumerate(raw_frames[:4]):
        path = _cache_path("anim", f"{cache_key}_f{i}")
        _save_to_cache(path, data)
        frames.append(f"data:image/png;base64,{base64.b64encode(data).decode()}")

    # Pad to 4 frames for smooth loop
    while len(frames) < 4 and frames:
        frames.append(frames[-1])
    return frames[:4]


def generate_actor_sprite(actor_id: str, name: str, role: str) -> Optional[str]:
    """
    Generate a character sprite for an actor.
    Returns base64 data URL or None on failure.
    Uses Gemini 2.0 Flash image generation (free tier).
    """
    cache_key = f"{_safe_filename(actor_id)}_{_safe_filename(role)}"
    cache_path = _cache_path("actor", cache_key)
    cached = _load_from_cache(cache_path)
    if cached is not None:
        return cached

    client_info = _get_genai_client()
    if client_info[0] != "genai":
        return None

    _, client, types = client_info
    prompt = (
        f"Create a professional character portrait illustration: {name}, {role} in a workplace setting. "
        "Flat illustration style, neutral expression, simple background. "
        "Square 1:1 composition, face and shoulders, suitable for a circular avatar. "
        "Corporate training simulation style. No text in the image."
    )
    data = _generate_image_gemini(client, types, prompt, "1:1")
    if data:
        _save_to_cache(cache_path, data)
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    return None


def get_scenario_setting(module_or_scenario_id: str) -> str:
    """Map module_id or scenario_id to a visual setting description."""
    settings = {
        # POSH
        "posh_bystander_001": "restaurant team lunch, colleagues at a table",
        "posh_microaggression_in_standups_001": "office stand-up meeting, team in open plan",
        "posh_customer_crossing_line_001": "customer service desk, office lobby",
        "posh_team_offsite_001": "conference room, team offsite retreat",
        # Cybersecurity
        "cybersecurity_password_reuse_boss_001": "office desk with computer, IT environment",
        "cybersecurity_usb_in_lobby_001": "office lobby, front desk area",
        "cybersecurity_wifi_trap_001": "airport gate, cafe or coworking space, public WiFi",
        # Ethics
        "ethics_data_for_discount_001": "office meeting room, data on screen",
        "ethics_favor_for_a_friend_001": "office corridor, two colleagues talking",
        "ethics_side_gig_conflict_001": "home office, laptop, remote work setup",
        # Escalation
        "escalation_informal_complaint_001": "HR office, professional setting",
        "escalation_low_performer_vs_bias_001": "performance review room, manager and employee",
        "escalation_retaliation_risk_001": "office hallway, tense atmosphere",
        # Module-level fallbacks
        "posh": "professional office, team meeting",
        "cybersecurity": "office with computers, IT setting",
        "ethics": "office meeting room",
        "escalation": "HR office, professional setting",
    }
    return settings.get(module_or_scenario_id, "professional office, neutral workplace")
