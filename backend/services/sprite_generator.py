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
from typing import Optional

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


def _cache_path(category: str, key: str) -> Path:
    return _get_cache_dir() / f"{category}_{key}.png"


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


def get_scenario_setting(module_id: str) -> str:
    """Map module/scenario to a visual setting description."""
    settings = {
        "posh-bystander": "restaurant team lunch, colleagues at a table",
        "posh-microaggression": "office stand-up meeting, team in open plan",
        "posh-customer": "customer service desk, office lobby",
        "posh-offsite": "conference room, team offsite retreat",
        "security-password": "office desk with computer, IT environment",
        "security-usb": "office lobby, front desk area",
        "security-wifi": "cafe or coworking space, public WiFi",
        "ethics-data": "office meeting room, data on screen",
        "ethics-favor": "office corridor, two colleagues talking",
        "ethics-sidegig": "home office, laptop, remote work setup",
        "escalation-informal": "HR office, professional setting",
        "escalation-bias": "performance review room, manager and employee",
        "escalation-retaliation": "office hallway, tense atmosphere",
    }
    return settings.get(module_id, "professional office, neutral workplace")
