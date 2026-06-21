"""TTS router — Phase 16 ElevenLabs voice synthesis endpoints for HELIOS."""
from __future__ import annotations

import requests as _requests
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/tts", tags=["tts"])


# ---------------------------------------------------------------------------
# Pydantic request bodies
# ---------------------------------------------------------------------------

class SynthBody(BaseModel):
    text: str
    voice_id: Optional[str] = None
    language: Optional[str] = None
    model: str = "eleven_multilingual_v2"
    stability: float = 0.5
    similarity_boost: float = 0.75
    speed: float = 1.0


class PronounceBody(BaseModel):
    word: str
    language: str


class LessonBody(BaseModel):
    text: str
    language: str


class BriefingBody(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/synthesize")
def synthesize(body: SynthBody):
    try:
        from tts.elevenlabs import synthesize as tts_synthesize
        return tts_synthesize(
            body.text,
            body.voice_id,
            body.language,
            body.model,
            body.stability,
            body.similarity_boost,
            body.speed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except _requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pronounce")
def pronounce(body: PronounceBody):
    try:
        from tts.elevenlabs import pronounce as tts_pronounce
        return tts_pronounce(body.word, body.language)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except _requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lesson")
def lesson(body: LessonBody):
    try:
        from tts.elevenlabs import speak_lesson
        return speak_lesson(body.text, body.language)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except _requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/briefing")
def briefing(body: BriefingBody):
    try:
        from tts.elevenlabs import speak_briefing
        return speak_briefing(body.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except _requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voices")
def voices():
    try:
        from tts.elevenlabs import get_voices
        return get_voices()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except _requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
def models():
    try:
        from tts.elevenlabs import get_models
        return get_models()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except _requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quota")
def quota():
    try:
        from tts.elevenlabs import check_quota
        return check_quota()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except _requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice-map")
def voice_map():
    try:
        from tts.elevenlabs import LANGUAGE_VOICES, VOICES
        return {"language_voices": LANGUAGE_VOICES, "voices": VOICES}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except _requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
