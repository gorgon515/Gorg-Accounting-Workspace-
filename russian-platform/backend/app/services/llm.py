"""LLM abstraction layer.

Every AI feature (tutor, conversation partner, content generation,
writing feedback) goes through this interface so providers swap without
touching feature code. Providers, in order of preference:

* ``LocalLlamaProvider`` — Phase 4 offline-first path. Speaks the
  OpenAI-compatible chat API served by ``llama.cpp`` (``llama-server``),
  Ollama, LM Studio, vLLM, and friends — i.e. any local GGUF/ONNX runner
  on localhost. No cloud, no key. GPU acceleration is the runner's
  concern, not ours.
* ``InProcessLlamaProvider`` — loads a GGUF directly via the optional
  ``llama-cpp-python`` package when installed (RLP_LLAMA_MODEL_PATH).
* ``AnthropicProvider`` — cloud path when RLP_ANTHROPIC_API_KEY is set.
* ``OfflineProvider`` — deterministic fallback: scripted dialogue trees,
  template-based practice generation over the seeded database. The
  platform is fully usable (and CI-testable) at this tier.

Selection is config-driven (``RLP_LLM_PROVIDER``) with graceful
degradation: a misconfigured/unreachable local provider degrades to
OfflineProvider rather than erroring feature code.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings

logger = logging.getLogger("rli.llm")


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


class LocalLlamaProvider(LLMProvider):
    """OpenAI-compatible chat completion against a local inference server
    (llama.cpp `llama-server`, Ollama, LM Studio, vLLM...)."""

    def __init__(self, base_url: str, model: str = "local"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    @property
    def is_generative(self) -> bool:
        return True

    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> str:
        response = httpx.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}, *messages],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
            timeout=300.0,  # CPU inference can be slow; that's fine offline
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def healthy(self) -> bool:
        try:
            probe = httpx.get(f"{self.base_url}/v1/models", timeout=3.0)
            return probe.status_code < 500
        except httpx.HTTPError:
            return False


class InProcessLlamaProvider(LLMProvider):
    """Loads a GGUF model in-process via the optional llama-cpp-python
    package. Heavier startup, zero extra processes — for packaged
    desktop deployments."""

    def __init__(self, model_path: str):
        from llama_cpp import Llama  # optional dependency, import-guarded

        self._llama = Llama(
            model_path=model_path, n_ctx=4096, verbose=False,
        )

    @property
    def is_generative(self) -> bool:
        return True

    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> str:
        result = self._llama.create_chat_completion(
            messages=[{"role": "system", "content": system}, *messages],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return result["choices"][0]["message"]["content"]


def get_llm_provider() -> LLMProvider:
    """Config-driven provider selection with graceful degradation.

    llama-cpp → local server (health-checked; degrades to offline)
    llama-gguf → in-process GGUF (degrades if package/model missing)
    anthropic → cloud Messages API
    anything else → deterministic offline tier
    """
    settings = get_settings()

    if settings.llm_provider == "llama-cpp" and settings.llama_url:
        provider = LocalLlamaProvider(settings.llama_url, settings.llama_model)
        if provider.healthy():
            return provider
        logger.warning(
            "local llama server at %s unreachable — degrading to offline tier",
            settings.llama_url,
        )
        return OfflineProvider()

    if settings.llm_provider == "llama-gguf" and settings.llama_model_path:
        try:
            return InProcessLlamaProvider(settings.llama_model_path)
        except (ImportError, OSError, ValueError) as exc:
            logger.warning(
                "in-process GGUF unavailable (%s) — degrading to offline tier", exc
            )
            return OfflineProvider()

    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)

    return OfflineProvider()
