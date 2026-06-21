"""ElevenLabs TTS — Phase 16 voice synthesis for HELIOS.

Env vars:
  ELEVENLABS_API_KEY  — ElevenLabs API key
"""
from __future__ import annotations
import base64
import os
import requests
from typing import Optional

_BASE = "https://api.elevenlabs.io/v1"

# Recommended multilingual voices
VOICES = {
    "rachel":    "21m00Tcm4TlvDq8ikWAM",  # English female
    "aria":      "9BWtsMINqrJLrRacOk9x",  # English female
    "george":    "JBFqnCBsd6RMkjVDRZzb",  # English male
    "callum":    "N2lVS1w4EtoT3dr4eOWO",  # English male
    "charlotte": "XB0fDUnXU5powFXDhCwa",  # English female
    "default":   "EXAVITQu4vr4xnSDxMaL",  # Sarah (default multilingual)
}

# Language to voice mapping for Language Academy
LANGUAGE_VOICES = {
    "russian":  "EXAVITQu4vr4xnSDxMaL",
    "spanish":  "EXAVITQu4vr4xnSDxMaL",
    "french":   "EXAVITQu4vr4xnSDxMaL",
    "german":   "EXAVITQu4vr4xnSDxMaL",
    "italian":  "EXAVITQu4vr4xnSDxMaL",
    "japanese": "EXAVITQu4vr4xnSDxMaL",
    "mandarin": "EXAVITQu4vr4xnSDxMaL",
    "english":  "21m00Tcm4TlvDq8ikWAM",
}


def _key() -> str:
    return os.getenv("ELEVENLABS_API_KEY", "")


def _headers(content_type: bool = True) -> dict:
    if content_type:
        return {"xi-api-key": _key(), "Content-Type": "application/json"}
    return {"xi-api-key": _key()}


def _check_key() -> None:
    if not _key():
        raise ValueError("ELEVENLABS_API_KEY not configured")


def synthesize(
    text: str,
    voice_id: Optional[str] = None,
    language: Optional[str] = None,
    model: str = "eleven_multilingual_v2",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    speed: float = 1.0,
) -> dict:
    _check_key()
    if not voice_id:
        voice_id = (
            LANGUAGE_VOICES.get(language, VOICES["default"])
            if language
            else VOICES["default"]
        )
    body = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "speed": speed,
        },
    }
    r = requests.post(
        f"{_BASE}/text-to-speech/{voice_id}",
        json=body,
        headers={**_headers(), "Accept": "audio/mpeg"},
        timeout=30,
    )
    r.raise_for_status()
    audio_b64 = base64.b64encode(r.content).decode()
    return {
        "audio_b64": audio_b64,
        "format": "mp3",
        "voice_id": voice_id,
        "model": model,
        "chars": len(text),
    }


def pronounce(word: str, language: str) -> dict:
    voice_id = LANGUAGE_VOICES.get(language, VOICES["default"])
    return synthesize(
        word,
        voice_id=voice_id,
        language=language,
        stability=0.3,
        similarity_boost=0.9,
        speed=0.85,
    )


def speak_lesson(text: str, language: str) -> dict:
    return synthesize(
        text,
        language=language,
        stability=0.6,
        similarity_boost=0.75,
        speed=0.9,
    )


def speak_briefing(text: str) -> dict:
    return synthesize(
        text,
        voice_id=VOICES["george"],
        stability=0.6,
        similarity_boost=0.8,
        speed=1.0,
    )


def get_voices() -> list:
    _check_key()
    r = requests.get(
        f"{_BASE}/voices",
        headers=_headers(content_type=False),
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("voices", [])


def get_models() -> list:
    _check_key()
    r = requests.get(
        f"{_BASE}/models",
        headers=_headers(content_type=False),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def check_quota() -> dict:
    _check_key()
    r = requests.get(
        f"{_BASE}/user/subscription",
        headers=_headers(content_type=False),
        timeout=10,
    )
    r.raise_for_status()
    d = r.json()
    return {
        "character_count": d.get("character_count", 0),
        "character_limit": d.get("character_limit", 0),
        "remaining": d.get("character_limit", 0) - d.get("character_count", 0),
        "tier": d.get("tier", "unknown"),
    }
