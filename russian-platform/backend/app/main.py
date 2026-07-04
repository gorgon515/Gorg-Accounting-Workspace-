"""Application entrypoint.

Run locally:
    uvicorn app.main:app --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    account,
    analytics,
    auth,
    conversation,
    exams,
    gamification,
    grammar,
    lessons,
    library,
    practice,
    reviews,
    vocabulary,
    writing,
)
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.seed.runner import seed_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rli")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.debug and (
        settings.secret_key == "dev-secret-change-in-production"
        or len(settings.secret_key) < 32
    ):
        logger.warning(
            "RLP_SECRET_KEY is missing or shorter than 32 bytes. Set a strong "
            "secret before exposing this server to real users."
        )
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_all(db)
    logger.info("Database ready and seeded")
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-powered Russian language institute: vocabulary, grammar, "
                "lessons, SRS, conversation, pronunciation, and analytics.",
    lifespan=lifespan,
)

@app.middleware("http")
async def server_timing(request, call_next):
    """Response-time visibility: Server-Timing header on every response,
    warning log for anything over 150 ms (the Phase 3 latency budget)."""
    import time

    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.1f}"
    if elapsed_ms > 150 and request.url.path.startswith("/api"):
        logger.warning("slow endpoint %s took %.0fms", request.url.path, elapsed_ms)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, vocabulary, grammar, lessons, reviews, conversation,
               practice, analytics, library, gamification, exams, writing,
               account):
    app.include_router(module.router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
