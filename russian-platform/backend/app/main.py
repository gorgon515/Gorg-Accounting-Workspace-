"""Application entrypoint.

Run locally:
    uvicorn app.main:app --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    analytics,
    auth,
    conversation,
    grammar,
    lessons,
    practice,
    reviews,
    vocabulary,
)
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.seed.runner import seed_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rli")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, vocabulary, grammar, lessons, reviews, conversation,
               practice, analytics):
    app.include_router(module.router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
