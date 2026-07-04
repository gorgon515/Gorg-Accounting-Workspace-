# AI Provider Guide

All generative features (tutor, free conversation, story generation,
writing enrichment) call one interface: `LLMProvider` in
`app/services/llm.py`. Selection is config-driven with graceful
degradation — a broken provider never breaks a feature, it lowers the
tier.

## Tiers

| Tier | Config | Notes |
|---|---|---|
| **Local server** (recommended, offline) | `RLP_LLM_PROVIDER=llama-cpp`, `RLP_LLAMA_URL=http://localhost:8080` | Any OpenAI-compatible runner: `llama-server -m model.gguf`, Ollama (`http://localhost:11434`), LM Studio, vLLM. Health-checked at selection; unreachable → offline tier with a log warning. GPU acceleration is the runner's concern. |
| **In-process GGUF** | `RLP_LLM_PROVIDER=llama-gguf`, `RLP_LLAMA_MODEL_PATH=/path/model.gguf`, `pip install llama-cpp-python` | For packaged desktop builds; degrades if the package or model is missing. |
| **Cloud** | `RLP_LLM_PROVIDER=anthropic`, `RLP_ANTHROPIC_API_KEY=…` | Anthropic Messages API. |
| **Offline deterministic** (default) | `RLP_LLM_PROVIDER=offline` | Scripted dialogue trees (12 scenarios), template-based quizzes/cloze from the DB, personalized tutor practice plans. Full platform works at this tier; CI runs here. |

## Recommended local models
Anything instruction-tuned with decent Russian: 7–9B Q4 GGUF quantizations
run on 8 GB RAM CPU-only (slow but usable; the client timeout is 300 s).

## The wire contract
Feature prompts instruct the model to reply as:

```
<Russian reply with stress marks>
---
<English translation>
###
[{"error": "...", "correction": "...", "explanation": "..."}]
```

Parsing is defensive: missing separators degrade to plain text, malformed
JSON degrades to no corrections (tested with `StubProvider` in
`tests/test_llm_paths.py`). Any new provider only needs `complete()` and
`is_generative` — the contract lives in feature prompts, not providers.

## Speech
STT/TTS follow the same pattern (`app/services/speech.py`): browser Web
Speech API by default (local in modern browsers), `WhisperSTTProvider`
for a self-hosted Whisper HTTP service.
