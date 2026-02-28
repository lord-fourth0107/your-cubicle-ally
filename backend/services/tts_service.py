"""
services/tts_service.py
----------------------
Generates speech from text using Google Gemini TTS.
Used to make actor dialogue play as live audio in the arena.

Requires GOOGLE_API_KEY. Uses gemini-2.5-flash-preview-tts or gemini-2.5-flash-tts.
"""

import os
import struct
from typing import Optional, Tuple

_tts_client = None

# Distinct voices per character (Gemini prebuilt: Kore, Charon, Puck)
VOICE_BY_ACTOR = {
    "default": "Kore",
    "mark": "Charon",
    "elena": "Kore",
    "marcus": "Puck",
    "claire": "Kore",
    "jordan": "Charon",
    "neel": "Puck",
    "sara": "Kore",
    "vik": "Puck",
    "meera": "Kore",
    "riya": "Kore",
    "kabir": "Charon",
    "sana": "Kore",
    "harsh": "Puck",
    "deepa": "Kore",
    "imran": "Charon",
    "jae": "Kore",
    "ron": "Puck",
    "rohan": "Charon",
    "nisha": "Kore",
    "dev": "Puck",
    "isha": "Kore",
    "mira": "Kore",
    "kunal": "Charon",
}

VOICE_POOL = ["Kore", "Charon", "Puck"]


def _voice_for_actor(actor_id: Optional[str]) -> str:
    if not actor_id:
        return VOICE_BY_ACTOR["default"]
    key = actor_id.lower().strip()
    if key in VOICE_BY_ACTOR:
        return VOICE_BY_ACTOR[key]
    return VOICE_POOL[hash(key) % len(VOICE_POOL)]


def _get_tts_client():
    global _tts_client
    if _tts_client is not None:
        return _tts_client
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        _tts_client = ("none", None)
        return _tts_client
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        _tts_client = ("genai", client, types)
        return _tts_client
    except Exception:
        _tts_client = ("none", None)
        return _tts_client


def _linear16_to_wav(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
    """Wrap raw LINEAR16 (16-bit PCM) in a WAV header for browser playback."""
    num_samples = len(pcm_data) // 2
    byte_rate = sample_rate * 2
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        byte_rate,
        2,
        16,
        b"data",
        data_size,
    )
    return header + pcm_data


def generate_speech(text: str, actor_id: Optional[str] = None) -> Optional[Tuple[bytes, str]]:
    """
    Generate speech from text using Gemini TTS.
    Returns (audio_bytes, mime_type) or None on failure.
    """
    if not text or not text.strip():
        return None

    client_info = _get_tts_client()
    if client_info[0] != "genai":
        return None

    _, client, types = client_info
    voice_name = _voice_for_actor(actor_id)
    model = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

    try:
        # Style hint for workplace conversation
        prompt = f"Say this naturally, as in a professional conversation: {text.strip()}"
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    ),
                ),
            ),
        )
        if not response.candidates:
            return None
        parts = response.candidates[0].content.parts
        if not parts:
            return None
        part = parts[0]
        if not hasattr(part, "inline_data") or not part.inline_data:
            return None
        data = part.inline_data.data
        mime = getattr(part.inline_data, "mime_type", None) or "audio/wav"

        # Gemini may return raw LINEAR16; wrap in WAV if needed
        if mime == "audio/pcm" or mime == "audio/l16" or (mime == "audio/wav" and len(data) < 44):
            data = _linear16_to_wav(data)
            mime = "audio/wav"

        return (data, mime)
    except Exception as e:
        print(f"[tts_service] Gemini TTS failed: {e}")
        return None
