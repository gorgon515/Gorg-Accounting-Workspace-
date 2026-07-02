"""LLM abstraction layer.

Every AI feature (conversation partner, content generation, writing
feedback) goes through this interface so providers can be swapped without
touching feature code. Two providers ship in Phase 1:

* ``AnthropicProvider`` — production path, used when RLP_ANTHROPIC_API_KEY
  is set. Calls the Messages API over HTTPS.
* ``OfflineProvider`` — deterministic fallback so the whole platform works
  (and is testable in CI) with no network or key. Conversation scenarios
  fall back to their scripted dialogue trees, content generation falls
  back to template-based composition over the seeded database.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> str:
        """messages: [{"role": "user"|"assistant", "content": str}, ...]"""

    @property
    @abstractmethod
    def is_generative(self) -> bool:
        """True if this provider can produce novel free-form text."""


class OfflineProvider(LLMProvider):
    """Deterministic provider used without an API key. Feature code checks
    ``is_generative`` and routes to scripted/templated behavior instead of
    calling ``complete``."""

    @property
    def is_generative(self) -> bool:
        return False

    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> str:
        raise RuntimeError(
            "OfflineProvider cannot generate free-form text; callers must "
            "check is_generative and use scripted fallbacks."
        )


class AnthropicProvider(LLMProvider):
    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @property
    def is_generative(self) -> bool:
        return True

    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> str:
        response = httpx.post(
            self.API_URL,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "system": system,
                "messages": messages,
                "max_tokens": max_tokens,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return "".join(
            block["text"] for block in data["content"] if block["type"] == "text"
        )


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)
    return OfflineProvider()
