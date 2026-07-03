"""Reading/listening library: graded texts with clickable words, dictation
grading, per-text vocabulary extraction, and reading-position bookmarks."""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Bookmark, Card, LearningEvent, Lexeme, Text, User
from app.services.gamification import touch_streak
from app.services.speech import score_pronunciation, strip_stress

router = APIRouter(prefix="/library", tags=["library"])


def _tokenize(sentence: str) -> list[str]:
    return re.findall(r"[а-яёА-ЯЁ-]+", strip_stress(sentence).lower())


@router.get("/texts")
def list_texts(
    cefr: str | None = None,
    kind: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Text).order_by(Text.cefr_level, Text.slug)
    if cefr:
        stmt = stmt.where(Text.cefr_level == cefr)
    if kind:
        stmt = stmt.where(Text.kind == kind)
    texts = db.scalars(stmt).all()
    bookmarks = {
        b.text_id: b.sentence_index
        for b in db.scalars(select(Bookmark).where(Bookmark.user_id == user.id))
    }
    return [
        {
            "slug": t.slug,
            "title": t.title,
            "title_translation": t.title_translation,
            "kind": t.kind,
            "cefr_level": t.cefr_level,
            "topic": t.topic,
            "summary": t.summary,
            "sentence_count": len(t.sentences),
            "word_count": t.word_count,
            "bookmark": bookmarks.get(t.id),
        }
        for t in texts
    ]


@router.get("/texts/{slug}")
def get_text(
    slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    text = db.scalar(select(Text).where(Text.slug == slug))
    if text is None:
        raise HTTPException(404, "Text not found")

    # Map every token to a dictionary entry where one exists, so the reader
    # can make words clickable (hover dictionary + add-to-SRS).
    tokens = {tok for sent in text.sentences for tok in _tokenize(sent["ru"])}
    lexemes = db.scalars(select(Lexeme).where(Lexeme.lemma.in_(tokens))).all()
    known_cards = set(
        db.scalars(
            select(Card.lexeme_id).where(
                Card.user_id == user.id, Card.card_type == "vocabulary"
            )
        )
    )
    bookmark = db.scalar(
        select(Bookmark).where(
            Bookmark.user_id == user.id, Bookmark.text_id == text.id
        )
    )
    db.add(
        LearningEvent(
            user_id=user.id,
            event_type="reading",
            skill="reading",
            payload={"text": slug},
        )
    )
    touch_streak(user)
    db.commit()
    return {
        "slug": text.slug,
        "title": text.title,
        "title_translation": text.title_translation,
        "kind": text.kind,
        "cefr_level": text.cefr_level,
        "summary": text.summary,
        "sentences": text.sentences,
        "bookmark": bookmark.sentence_index if bookmark else 0,
        "glossary": {
            l.lemma: {
                "id": l.id,
                "stressed": l.stressed,
                "translation": l.translation,
                "part_of_speech": l.part_of_speech,
                "in_srs": l.id in known_cards,
            }
            for l in lexemes
        },
    }


class BookmarkRequest(BaseModel):
    sentence_index: int = Field(ge=0)


@router.put("/texts/{slug}/bookmark")
def set_bookmark(
    slug: str,
    payload: BookmarkRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    text = db.scalar(select(Text).where(Text.slug == slug))
    if text is None:
        raise HTTPException(404, "Text not found")
    bookmark = db.scalar(
        select(Bookmark).where(
            Bookmark.user_id == user.id, Bookmark.text_id == text.id
        )
    )
    if bookmark is None:
        bookmark = Bookmark(user_id=user.id, text_id=text.id)
        db.add(bookmark)
    bookmark.sentence_index = payload.sentence_index
    db.commit()
    return {"slug": slug, "sentence_index": bookmark.sentence_index}


class AddWordRequest(BaseModel):
    lexeme_id: int


@router.post("/add-word", status_code=201)
def add_word_to_srs(
    payload: AddWordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Enroll a word met while reading into the SRS queue (LingQ-style)."""
    lexeme = db.get(Lexeme, payload.lexeme_id)
    if lexeme is None:
        raise HTTPException(404, "Lexeme not found")
    existing = db.scalar(
        select(Card).where(
            Card.user_id == user.id,
            Card.lexeme_id == lexeme.id,
            Card.card_type == "vocabulary",
        )
    )
    if existing:
        return {"created": False, "card_id": existing.id}
    card = Card(user_id=user.id, lexeme_id=lexeme.id)
    db.add(card)
    db.commit()
    return {"created": True, "card_id": card.id}


class DictationRequest(BaseModel):
    sentence_index: int = Field(ge=0)
    typed_text: str


@router.post("/texts/{slug}/dictation")
def check_dictation(
    slug: str,
    payload: DictationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Grade a dictation attempt against the target sentence — same word
    alignment used for pronunciation, applied to typed text."""
    text = db.scalar(select(Text).where(Text.slug == slug))
    if text is None:
        raise HTTPException(404, "Text not found")
    if payload.sentence_index >= len(text.sentences):
        raise HTTPException(400, "sentence_index out of range")
    target = text.sentences[payload.sentence_index]["ru"]
    result = score_pronunciation(target, payload.typed_text)
    db.add(
        LearningEvent(
            user_id=user.id,
            event_type="listening",
            skill="listening",
            payload={"text": slug, "mode": "dictation",
                     "score": result["overall_score"]},
        )
    )
    touch_streak(user)
    db.commit()
    return {**result, "target": target}
