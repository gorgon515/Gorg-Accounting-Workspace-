"""Application configuration.

All settings can be overridden via environment variables (prefix RLP_)
or a local .env file. Defaults favor a zero-config local development
experience (SQLite); production deployments point DATABASE_URL at
PostgreSQL and REDIS_URL at Redis without code changes.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RLP_", env_file=".env", extra="ignore"
    )

    app_name: str = "Russian Language Institute"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False

    # Persistence. SQLite for local dev; set to a postgresql+psycopg URL in prod.
    database_url: str = "sqlite:///./rli.db"
    redis_url: str | None = None

    # Auth
    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7
    algorithm: str = "HS256"

    # LLM / speech provider abstraction. Default = deterministic offline
    # tier (scripted dialogues, template generation). Local inference is
    # the preferred generative tier (offline-first, Phase 4).
    llm_provider: str = "offline"  # offline | llama-cpp | llama-gguf | anthropic
    llama_url: str | None = None  # OpenAI-compatible server, e.g. http://localhost:8080
    llama_model: str = "local"
    llama_model_path: str | None = None  # .gguf path for in-process loading
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    stt_provider: str = "offline"  # offline | whisper
    tts_provider: str = "offline"  # offline | external

    # Content packs: shared HMAC key for pack signing/verification.
    pack_key: str | None = None

    # SRS tuning
    srs_target_retention: float = 0.9
    srs_max_interval_days: int = 365

    # Gamification
    xp_per_new_word: int = 10
    xp_per_review: int = 2
    xp_per_lesson: int = 50
    xp_per_conversation_turn: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
