"""Daily Language Coach — a persisted, deterministic daily plan per language.

``today`` assembles a six-section plan (lesson, vocabulary, review, conversation,
listening, assessment) chosen deterministically from the (language, date) pair,
and persists it so repeated calls on the same day return the identical plan.
"""
from __future__ import annotations

import json
import sqlite3
import hashlib
from datetime import date
from pathlib import Path
from typing import Optional

from . import content as C

_DB = Path(".data/language_coach.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS coach_plan (
            id TEXT PRIMARY KEY,
            language TEXT NOT NULL,
            day TEXT NOT NULL,
            plan TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(language, day)
        );
    """)
    return conn


class DailyCoach:
    def __init__(self):
        _conn().close()

    def _seed(self, language: str, day: str) -> int:
        h = hashlib.sha1(f"{language}:{day}".encode()).hexdigest()
        return int(h[:8], 16)

    def today(self, language: str, day: Optional[str] = None) -> dict:
        if language not in C.LANGUAGE_CODES:
            raise ValueError(f"unknown language: {language}")
        day = day or date.today().isoformat()
        pid = hashlib.sha1(f"{language}:{day}".encode()).hexdigest()[:16]

        conn = _conn()
        row = conn.execute("SELECT plan FROM coach_plan WHERE id=?", (pid,)).fetchone()
        if row:
            conn.close()
            return json.loads(row["plan"])
        conn.close()

        plan = self._build(language, day)
        conn = _conn()
        conn.execute(
            "INSERT OR IGNORE INTO coach_plan (id, language, day, plan) VALUES (?,?,?,?)",
            (pid, language, day, json.dumps(plan)))
        conn.commit()
        # Re-read to guarantee a single canonical record across concurrent calls.
        row = conn.execute("SELECT plan FROM coach_plan WHERE id=?", (pid,)).fetchone()
        conn.close()
        return json.loads(row["plan"]) if row else plan

    def _build(self, language: str, day: str) -> dict:
        seed = self._seed(language, day)

        # Deterministic selections from the seed.
        level = C.LEVELS[seed % len(C.LEVELS)]
        topic = C.TOPIC_IDS[seed % len(C.TOPIC_IDS)]
        scenario = C.CONVERSATION_SCENARIOS[seed % len(C.CONVERSATION_SCENARIOS)]
        listening = C.LISTENING[seed % len(C.LISTENING)]

        # Lesson summary.
        from .lessons import lesson_id
        lang_name = next((l["name"] for l in C.LANGUAGES if l["code"] == language), language)
        topic_name = (C.topic_meta(topic) or {}).get("name", topic)
        lesson = {
            "id": lesson_id(language, level, topic),
            "title": f"{lang_name} {level}: {topic_name}",
            "language": language, "level": level, "topic": topic,
        }

        # New vocabulary to learn (deterministic slice from the topic).
        topic_words = C.VOCAB.get(topic, [])
        start = seed % max(1, len(topic_words))
        picked = (topic_words + topic_words)[start:start + 5]
        vocabulary = [{"word": w["word"], "translation": w["translations"].get(language, ""),
                       "definition": w["definition"], "cefr": w["cefr"]} for w in picked]

        # Due SRS cards.
        from .vocabulary import get_vocabulary_system
        try:
            review = get_vocabulary_system().review(language, limit=5)
        except Exception:
            review = []

        # Conversation.
        conversation = {"scenario": scenario["id"], "title": scenario["title"],
                        "setup": scenario["setup"], "target_vocab": scenario["target_vocab"]}

        # Listening.
        listening_item = {"id": listening["id"], "title": listening["title"],
                          "level": listening["level"], "language": language,
                          "question_count": len(listening["questions"])}

        # Short assessment quiz from the topic vocab.
        quiz_q = []
        for w in picked[:3]:
            ans = w["translations"].get(language, "")
            distractors = [o["translations"].get(language, "") for o in topic_words
                           if o["word"] != w["word"] and o["translations"].get(language, "")][:3]
            options = list(dict.fromkeys([ans] + distractors))
            quiz_q.append({"q": f"Translate '{w['word']}'", "options": options, "answer": ans})
        assessment = {"title": f"Daily {lang_name} quiz", "questions": quiz_q,
                      "passing_score": 0.7}

        return {
            "date": day,
            "language": language,
            "lesson": lesson,
            "vocabulary": vocabulary,
            "review": review,
            "conversation": conversation,
            "listening": listening_item,
            "assessment": assessment,
        }

    def stats(self) -> dict:
        conn = _conn()
        plans = conn.execute("SELECT COUNT(*) FROM coach_plan").fetchone()[0]
        by_lang = {r["language"]: r["c"] for r in conn.execute(
            "SELECT language, COUNT(*) c FROM coach_plan GROUP BY language").fetchall()}
        conn.close()
        return {"plans": plans, "by_language": by_lang}


_instance: Optional[DailyCoach] = None


def get_daily_coach() -> DailyCoach:
    global _instance
    if _instance is None:
        _instance = DailyCoach()
    return _instance
