"""
services/sprite_generator.py
----------------------------
Generates sprites and environment art using Google Gemini/Imagen.
Creates a simulated world for the compliance training arena.
"""

import os
import base64
import io
from typing import Optional

_imagen_client = None


def _get_imagen_client():
    global _imagen_client
    if _imagen_client is not None:
        return _imagen_client
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        _imagen_client = ("none", None)
        return _imagen_client
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        _imagen_client = ("genai", client, types)
        return _imagen_client
    except ImportError:
        _imagen_client = ("none", None)
        return _imagen_client
    except Exception:
        _imagen_client = ("none", None)
        return _imagen_client


def _image_to_base64_data_url(img) -> Optional[str]:
    """Extract base64 data URL from generated image object."""
    try:
        if hasattr(img, "image"):
            im = img.image
        else:
            im = img
        if hasattr(im, "_image_bytes"):
            data = im._image_bytes
        elif hasattr(im, "image_bytes"):
            data = im.image_bytes
        elif hasattr(im, "save"):
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            data = buf.getvalue()
        else:
            return None
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except Exception:
        return None


def generate_environment_image(module_id: str, scenario_setting: str) -> Optional[str]:
    """
    Generate an environment/setting image for the scenario.
    Returns base64 data URL or None on failure.
    """
    client_info = _get_imagen_client()
    if client_info[0] != "genai":
        return None

    _, client, types = client_info
    try:
        prompt = (
            f"Professional workplace setting: {scenario_setting}. "
            "Soft isometric or top-down view, warm lighting, "
            "clean vector illustration style, suitable for a training simulation."
        )
        model = os.getenv("IMAGEN_MODEL", "imagen-3.0-fast-generate-001")
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
            ),
        )
        if response.generated_images:
            return _image_to_base64_data_url(response.generated_images[0])
    except Exception as e:
        print(f"[sprite_generator] Environment image failed: {e}")
    return None


def generate_actor_sprite(actor_id: str, name: str, role: str) -> Optional[str]:
    """
    Generate a character sprite for an actor.
    Returns base64 data URL or None on failure.
    """
    client_info = _get_imagen_client()
    if client_info[0] != "genai":
        return None

    _, client, types = client_info
    try:
        prompt = (
            f"Professional character portrait of {name}, {role} in workplace. "
            "Flat illustration style, neutral expression, simple background, "
            "circular crop suitable for avatar, corporate training simulation."
        )
        model = os.getenv("IMAGEN_MODEL", "imagen-3.0-fast-generate-001")
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
            ),
        )
        if response.generated_images:
            return _image_to_base64_data_url(response.generated_images[0])
    except Exception as e:
        print(f"[sprite_generator] Actor sprite failed for {actor_id}: {e}")
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
