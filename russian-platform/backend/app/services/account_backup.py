"""Account backup: export, encrypted backup, and progress-safe restore.

Design rules:

* **Portable identifiers** — cards reference lemmas, completions reference
  lesson slugs, mastery references topic slugs. A backup restores onto a
  fresh install (or another device) even though row ids differ.
* **Never lose progress** — restore is a MERGE with per-record conflict
  resolution that always keeps the stronger side: max stability/reps for
  cards, max mastery, union of achievements/completions/exam results,
  max XP/streak. There is deliberately no "replace" mode.
* **Encryption** — optional password → PBKDF2-HMAC-SHA256 (600k
  iterations) → Fernet (AES-128-CBC + HMAC). Wrong password fails loudly.
"""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Achievement,
    Bookmark,
    Card,
    ExamResult,
    GrammarMastery,
    GrammarTopic,
    LessonCompletion,
    Lesson,
    Lexeme,
    Text,
    User,
    UserAchievement,
)
from app.services.text_utils import ensure_utc

BACKUP_FORMAT = 1


def export_account(db: Session, user: User) -> dict:
    lexeme_lemmas = {
        l.id: l.lemma for l in db.scalars(select(Lexeme))
    }
    lesson_slugs = {l.id: l.slug for l in db.scalars(select(Lesson))}
    topic_slugs = {t.id: t.slug for t in db.scalars(select(GrammarTopic))}
    text_slugs = {t.id: t.slug for t in db.scalars(select(Text))}
    achievement_slugs = {a.id: a.slug for a in db.scalars(select(Achievement))}

    cards = [
        {
            "lemma": lexeme_lemmas.get(c.lexeme_id),
            "card_type": c.card_type, "direction": c.direction,
            "stability": c.stability, "difficulty": c.difficulty,
            "reps": c.reps, "lapses": c.lapses, "state": c.state,
            "due_at": ensure_utc(c.due_at).isoformat(),
            "last_reviewed_at": ensure_utc(c.last_reviewed_at).isoformat()
            if c.last_reviewed_at else None,
        }
        for c in db.scalars(select(Card).where(Card.user_id == user.id))
        if c.lexeme_id in lexeme_lemmas
    ]
    completions = [
        {
            "lesson_slug": lesson_slugs.get(c.lesson_id),
            "score": c.score, "passed": c.passed,
            "completed_at": ensure_utc(c.completed_at).isoformat(),
        }
        for c in db.scalars(
            select(LessonCompletion).where(LessonCompletion.user_id == user.id)
        )
        if c.lesson_id in lesson_slugs
    ]
    mastery = [
        {
            "topic_slug": topic_slugs.get(m.topic_id),
            "mastery": m.mastery, "attempts": m.attempts, "correct": m.correct,
        }
        for m in db.scalars(
            select(GrammarMastery).where(GrammarMastery.user_id == user.id)
        )
        if m.topic_id in topic_slugs
    ]
    achievements = [
        {
            "slug": achievement_slugs.get(ua.achievement_id),
            "earned_at": ensure_utc(ua.earned_at).isoformat(),
        }
        for ua in db.scalars(
            select(UserAchievement).where(UserAchievement.user_id == user.id)
        )
        if ua.achievement_id in achievement_slugs
    ]
    bookmarks = [
        {"text_slug": text_slugs.get(b.text_id), "sentence_index": b.sentence_index}
        for b in db.scalars(select(Bookmark).where(Bookmark.user_id == user.id))
        if b.text_id in text_slugs
    ]
    exams = [
        {
            "kind": e.kind, "level": e.level, "seed": e.seed,
            "score": e.score, "passed": e.passed, "sections": e.sections,
            "taken_at": ensure_utc(e.taken_at).isoformat(),
        }
        for e in db.scalars(select(ExamResult).where(ExamResult.user_id == user.id))
    ]

    return {
        "format": BACKUP_FORMAT,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": {
            "display_name": user.display_name,
            "cefr_estimate": user.cefr_estimate,
            "xp": user.xp,
            "streak_days": user.streak_days,
            "daily_goal_minutes": user.daily_goal_minutes,
            "ui_immersion_ratio": user.ui_immersion_ratio,
            "preferences": user.preferences or {},
        },
        "cards": cards,
        "completions": completions,
        "grammar_mastery": mastery,
        "achievements": achievements,
        "bookmarks": bookmarks,
        "exam_results": exams,
    }


def restore_account(db: Session, user: User, backup: dict) -> dict:
    """Merge a backup into this account. Every rule keeps the stronger
    side, so restoring an old backup can never regress progress."""
    if backup.get("format") != BACKUP_FORMAT:
        raise ValueError(f"unsupported backup format {backup.get('format')}")

    stats = {"cards_created": 0, "cards_merged": 0, "completions_added": 0,
             "mastery_merged": 0, "achievements_added": 0, "bookmarks": 0,
             "exams_added": 0}

    profile = backup.get("profile", {})
    user.xp = max(user.xp, int(profile.get("xp", 0)))
    user.streak_days = max(user.streak_days, int(profile.get("streak_days", 0)))
    levels = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"]
    imported_level = profile.get("cefr_estimate", "A0")
    if imported_level in levels and levels.index(imported_level) > levels.index(
        user.cefr_estimate
    ):
        user.cefr_estimate = imported_level
    user.preferences = {**(profile.get("preferences") or {}),
                        **(user.preferences or {})}

    lexemes_by_lemma = {l.lemma: l.id for l in db.scalars(select(Lexeme))}
    existing_cards = {
        (c.lexeme_id, c.card_type, c.direction): c
        for c in db.scalars(select(Card).where(Card.user_id == user.id))
    }
    for entry in backup.get("cards", []):
        lexeme_id = lexemes_by_lemma.get(entry.get("lemma"))
        if lexeme_id is None:
            continue  # content pack for this word not installed here
        key = (lexeme_id, entry["card_type"], entry["direction"])
        due = datetime.fromisoformat(entry["due_at"])
        last = (datetime.fromisoformat(entry["last_reviewed_at"])
                if entry.get("last_reviewed_at") else None)
        card = existing_cards.get(key)
        if card is None:
            db.add(Card(
                user_id=user.id, lexeme_id=lexeme_id,
                card_type=entry["card_type"], direction=entry["direction"],
                stability=entry["stability"], difficulty=entry["difficulty"],
                reps=entry["reps"], lapses=entry["lapses"], state=entry["state"],
                due_at=due, last_reviewed_at=last,
            ))
            stats["cards_created"] += 1
        else:
            # Stronger memory wins; lapses accumulate (they both happened).
            if entry["reps"] > card.reps or entry["stability"] > card.stability:
                card.stability = max(card.stability, entry["stability"])
                card.reps = max(card.reps, entry["reps"])
                card.state = entry["state"] if entry["reps"] > card.reps else card.state
                if last and (card.last_reviewed_at is None
                             or last > ensure_utc(card.last_reviewed_at)):
                    card.last_reviewed_at = last
                    card.due_at = due
                stats["cards_merged"] += 1

    lessons_by_slug = {l.slug: l.id for l in db.scalars(select(Lesson))}
    existing_completions = {
        (c.lesson_id, ensure_utc(c.completed_at).isoformat())
        for c in db.scalars(
            select(LessonCompletion).where(LessonCompletion.user_id == user.id)
        )
    }
    for entry in backup.get("completions", []):
        lesson_id = lessons_by_slug.get(entry.get("lesson_slug"))
        if lesson_id is None or (lesson_id, entry["completed_at"]) in existing_completions:
            continue
        db.add(LessonCompletion(
            user_id=user.id, lesson_id=lesson_id, score=entry["score"],
            passed=entry["passed"],
            completed_at=datetime.fromisoformat(entry["completed_at"]),
        ))
        stats["completions_added"] += 1

    topics_by_slug = {t.slug: t.id for t in db.scalars(select(GrammarTopic))}
    existing_mastery = {
        m.topic_id: m
        for m in db.scalars(
            select(GrammarMastery).where(GrammarMastery.user_id == user.id)
        )
    }
    for entry in backup.get("grammar_mastery", []):
        topic_id = topics_by_slug.get(entry.get("topic_slug"))
        if topic_id is None:
            continue
        record = existing_mastery.get(topic_id)
        if record is None:
            db.add(GrammarMastery(
                user_id=user.id, topic_id=topic_id, mastery=entry["mastery"],
                attempts=entry["attempts"], correct=entry["correct"],
            ))
        else:
            record.mastery = max(record.mastery, entry["mastery"])
            record.attempts = max(record.attempts, entry["attempts"])
            record.correct = max(record.correct, entry["correct"])
        stats["mastery_merged"] += 1

    achievements_by_slug = {a.slug: a.id for a in db.scalars(select(Achievement))}
    earned = set(db.scalars(
        select(UserAchievement.achievement_id).where(
            UserAchievement.user_id == user.id
        )
    ))
    for entry in backup.get("achievements", []):
        achievement_id = achievements_by_slug.get(entry.get("slug"))
        if achievement_id and achievement_id not in earned:
            db.add(UserAchievement(
                user_id=user.id, achievement_id=achievement_id,
                earned_at=datetime.fromisoformat(entry["earned_at"]),
            ))
            earned.add(achievement_id)
            stats["achievements_added"] += 1

    texts_by_slug = {t.slug: t.id for t in db.scalars(select(Text))}
    existing_bookmarks = {
        b.text_id: b
        for b in db.scalars(select(Bookmark).where(Bookmark.user_id == user.id))
    }
    for entry in backup.get("bookmarks", []):
        text_id = texts_by_slug.get(entry.get("text_slug"))
        if text_id is None:
            continue
        bookmark = existing_bookmarks.get(text_id)
        if bookmark is None:
            db.add(Bookmark(user_id=user.id, text_id=text_id,
                            sentence_index=entry["sentence_index"]))
        else:
            bookmark.sentence_index = max(bookmark.sentence_index,
                                          entry["sentence_index"])
        stats["bookmarks"] += 1

    existing_exams = {
        (e.kind, e.level, e.seed)
        for e in db.scalars(select(ExamResult).where(ExamResult.user_id == user.id))
    }
    for entry in backup.get("exam_results", []):
        key = (entry["kind"], entry["level"], entry["seed"])
        if key in existing_exams:
            continue
        db.add(ExamResult(
            user_id=user.id, kind=entry["kind"], level=entry["level"],
            seed=entry["seed"], score=entry["score"], passed=entry["passed"],
            sections=entry.get("sections", {}),
            taken_at=datetime.fromisoformat(entry["taken_at"]),
        ))
        stats["exams_added"] += 1

    db.commit()
    return stats


# ------------------------------------------------------------- encryption
def encrypt_backup(backup: dict, password: str) -> dict:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=600_000)
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    token = Fernet(key).encrypt(
        json.dumps(backup, ensure_ascii=False).encode()
    )
    return {
        "encrypted": True,
        "kdf": "pbkdf2-sha256-600k",
        "salt": base64.b64encode(salt).decode(),
        "payload": token.decode(),
    }


def decrypt_backup(envelope: dict, password: str) -> dict:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    salt = base64.b64decode(envelope["salt"])
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=600_000)
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    try:
        raw = Fernet(key).decrypt(envelope["payload"].encode())
    except InvalidToken as exc:
        raise ValueError("wrong password or corrupted backup") from exc
    return json.loads(raw)
