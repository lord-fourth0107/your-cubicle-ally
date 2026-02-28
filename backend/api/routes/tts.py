"""
api/routes/tts.py
----------------
Text-to-Speech endpoint for live audio dialogue.
Uses Gemini TTS to convert actor dialogue to speech.
"""

import base64
from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from services.tts_service import generate_speech

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    actor_id: str | None = None


@router.post("/speech")
async def tts_speech(body: TTSRequest):
    """
    Generate speech from text. Returns audio (WAV) as binary or base64.
    actor_id maps to distinct character voices.
    """
    result = generate_speech(body.text.strip(), body.actor_id)
    if result is None:
        return Response(
            content=b"",
            status_code=503,
            media_type="text/plain",
        )
    audio_bytes, mime_type = result
    return Response(
        content=audio_bytes,
        media_type=mime_type,
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.post("/speech/base64")
async def tts_speech_base64(body: TTSRequest):
    """
    Generate speech and return as base64 data URL (for easier frontend use).
    """
    result = generate_speech(body.text.strip(), body.actor_id)
    if result is None:
        return {"audio": None, "mime_type": None}
    audio_bytes, mime_type = result
    b64 = base64.b64encode(audio_bytes).decode()
    return {
        "audio": f"data:{mime_type};base64,{b64}",
        "mime_type": mime_type,
    }
