"""Speech layer: STT/TTS provider interfaces and pronunciation scoring.

Phase 1 ships the provider abstraction plus a transcript-based scorer:
the browser performs recognition (Web Speech API) or a Whisper service is
plugged in server-side, and the backend scores the recognized transcript
against the target utterance — word accuracy, ordering, and coverage —
producing per-word feedback. Acoustic phoneme-level scoring (formants,
stress detection from audio) is Phase 3 (see docs/ROADMAP.md).
"""
from __future__ import annotations

import re
import unicodedata
from abc import ABC, abstractmethod
from difflib import SequenceMatcher

STRESS_MARK = "́"


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes, language: str = "ru") -> str: ...


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: str = "female", speed: float = 1.0) -> bytes: ...


class WhisperSTTProvider(STTProvider):
    """Calls a self-hosted Whisper HTTP service (RLP_WHISPER_URL)."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def transcribe(self, audio_bytes: bytes, language: str = "ru") -> str:
        import httpx

        response = httpx.post(
            f"{self.base_url}/transcribe",
            files={"audio": ("audio.webm", audio_bytes)},
            data={"language": language},
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()["text"]


def strip_stress(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace(STRESS_MARK, ""))


def _words(text: str) -> list[str]:
    cleaned = re.sub(r"[^\wё\s-]", "", strip_stress(text).lower().replace("ё", "е"))
    return cleaned.split()


def score_pronunciation(target: str, recognized: str) -> dict:
    """Score a recognized transcript against the target utterance.

    Word-level alignment via SequenceMatcher gives per-word verdicts;
    fuzzy per-word similarity catches near-misses (един/один) so feedback
    can point at the specific word rather than failing the whole line.
    """
    target_words = _words(target)
    heard_words = _words(recognized)
    if not target_words:
        return {"overall_score": 0.0, "words": [], "feedback": []}

    matcher = SequenceMatcher(a=target_words, b=heard_words)
    word_results = [{"word": w, "status": "missed", "heard": None} for w in target_words]

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                word_results[i1 + offset].update(
                    status="correct", heard=heard_words[j1 + offset]
                )
        elif tag == "replace":
            for offset in range(i2 - i1):
                heard = heard_words[j1 + offset] if j1 + offset < j2 else None
                entry = word_results[i1 + offset]
                if heard:
                    similarity = SequenceMatcher(
                        a=entry["word"], b=heard
                    ).ratio()
                    entry.update(
                        status="close" if similarity >= 0.7 else "wrong", heard=heard
                    )

    points = {"correct": 1.0, "close": 0.6, "wrong": 0.0, "missed": 0.0}
    score = 100.0 * sum(points[w["status"]] for w in word_results) / len(word_results)

    feedback = []
    for w in word_results:
        if w["status"] == "close":
            feedback.append(f"Almost: said «{w['heard']}», target «{w['word']}»")
        elif w["status"] == "wrong":
            feedback.append(f"Incorrect: said «{w['heard']}», target «{w['word']}»")
        elif w["status"] == "missed":
            feedback.append(f"Missing word: «{w['word']}»")

    return {
        "overall_score": round(score, 1),
        "words": word_results,
        "feedback": feedback,
    }
