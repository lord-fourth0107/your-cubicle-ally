"""
services/tts_service.py
----------------------
Generates speech from text using Google Gemini TTS.
Uses module context (actor name, persona) to pick gender-appropriate voices.

Requires GOOGLE_API_KEY. Uses gemini-2.5-flash-preview-tts or gemini-2.5-flash-tts.
"""

import os
import struct
import re
from typing import Optional, Tuple

_tts_client = None

# Gemini TTS voices by gender (Kore=♀, Charon/Puck=♂, etc.)
FEMALE_VOICES = ["Kore", "Zephyr", "Aoede", "Leda", "Callirrhoe"]
MALE_VOICES = ["Charon", "Puck", "Fenrir", "Orus", "Enceladus"]

# Gender mapping from scenario actor names (from module YAML)
GENDER_BY_ACTOR: dict[str, str] = {
    "mark": "male",
    "elena": "female",
    "marcus": "male",
    "claire": "female",
    "jordan": "male",
    "neel": "male",
    "sara": "female",
    "vik": "male",
    "meera": "female",
    "riya": "female",
    "kabir": "male",
    "sana": "female",
    "harsh": "male",
    "deepa": "female",
    "imran": "male",
    "jae": "female",
    "ron": "male",
    "rohan": "male",
    "nisha": "female",
    "priyank": "male",
    "lata": "female",
    "tanvi": "female",
    "omar": "male",
    "dev": "male",
    "isha": "female",
    "mira": "female",
    "kunal": "male",
}

# Fallback: names that are commonly gender-specific (for unknown actors)
_FEMALE_NAMES = {
    "alex", "alexis", "sarah", "jennifer", "emily", "jessica", "maria", "lisa",
    "anna", "sophie", "rachel", "amanda", "nicole", "rebecca", "victoria",
    "priya", "anita", "sunita", "kavita", "pooja", "neha", "divya",
}
_MALE_NAMES = {
    "alex", "michael", "david", "james", "john", "robert", "william",
    "daniel", "andrew", "ryan", "chris", "kevin", "sam", "eric",
    "raj", "amit", "arjun", "rahul", "vijay", "suresh",
}


def _infer_gender_from_name(name: str) -> str:
    """Infer gender from actor_id/name when not in explicit mapping."""
    n = name.lower().strip()
    if n in _FEMALE_NAMES and n not in _MALE_NAMES:
        return "female"
    if n in _MALE_NAMES:
        return "male"
    # Heuristic: many -a/-i/-ya endings are female across cultures
    if re.search(r"(a|i|ya|ee|na)$", n) and len(n) > 2:
        return "female"
    return "male"  # default assumption for ambiguous


def _gender_from_context(
    actor_id: Optional[str],
    persona: Optional[str] = None,
) -> str:
    """
    Determine gender from module context: explicit mapping, then persona keywords, then name.
    """
    key = (actor_id or "").lower().strip()
    if key in GENDER_BY_ACTOR:
        return GENDER_BY_ACTOR[key]

    if persona:
        p = persona.lower()
        if re.search(r"\b(she|her|woman|female)\b", p):
            return "female"
        if re.search(r"\b(he|him|his|man|male)\b", p):
            return "male"

    return _infer_gender_from_name(actor_id or "default")


def _voice_for_actor(
    actor_id: Optional[str],
    persona: Optional[str] = None,
) -> str:
    """Pick a gender-appropriate voice from Gemini TTS."""
    gender = _gender_from_context(actor_id, persona)
    pool = FEMALE_VOICES if gender == "female" else MALE_VOICES
    if not actor_id:
        return pool[0]
    return pool[hash((actor_id or "").lower()) % len(pool)]


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


def generate_speech(
    text: str,
    actor_id: Optional[str] = None,
    persona: Optional[str] = None,
) -> Optional[Tuple[bytes, str]]:
    """
    Generate speech from text using Gemini TTS.
    Uses actor_id and optional persona (from scenario) to pick gender-appropriate voice.
    Returns (audio_bytes, mime_type) or None on failure.
    """
    if not text or not text.strip():
        return None

    client_info = _get_tts_client()
    if client_info[0] != "genai":
        return None

    _, client, types = client_info
    voice_name = _voice_for_actor(actor_id, persona)
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
