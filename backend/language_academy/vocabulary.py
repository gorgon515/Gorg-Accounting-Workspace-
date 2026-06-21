"""Vocabulary System — expandable bank + SM-2 spaced repetition.

On first use the base ``content.VOCAB`` headwords are *expanded* into a
``vocab_entry`` table with one row per (headword × language). The SRS layer
implements the real SM-2 algorithm (ease factor, interval, repetitions,
due-date scheduling) over a ``vocab_review`` card table.
"""
from __future__ import annotations

import json
import sqlite3
import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from . import content as C

_DB = Path(".data/language_vocab.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS vocab_entry (
            id TEXT PRIMARY KEY,
            language TEXT NOT NULL,
            headword TEXT NOT NULL,
            word TEXT NOT NULL,
            translation TEXT NOT NULL,
            definition TEXT DEFAULT '',
            pos TEXT DEFAULT '',
            example TEXT DEFAULT '',
            cefr TEXT DEFAULT 'A1',
            frequency INTEGER DEFAULT 3,
            topic TEXT NOT NULL,
            UNIQUE(language, headword, topic)
        );
        CREATE TABLE IF NOT EXISTS vocab_review (
            card_id TEXT PRIMARY KEY,
            language TEXT NOT NULL,
            headword TEXT NOT NULL,
            topic TEXT DEFAULT '',
            ease REAL DEFAULT 2.5,
            interval INTEGER DEFAULT 0,
            reps INTEGER DEFAULT 0,
            due_date TEXT DEFAULT (date('now')),
            last_grade INTEGER DEFAULT -1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_entry_lang_topic ON vocab_entry(language, topic);
        CREATE INDEX IF NOT EXISTS idx_review_lang_due ON vocab_review(language, due_date);
    """)
    return conn


def _eid(language: str, headword: str, topic: str) -> str:
    return hashlib.sha1(f"{language}:{topic}:{headword}".encode()).hexdigest()[:16]


class VocabularySystem:
    def __init__(self):
        _conn().close()
        self.expand()

    # ── Expansion ────────────────────────────────────────────────────────────
    def expand(self) -> dict:
        """Materialize content.VOCAB into vocab_entry (idempotent)."""
        conn = _conn()
        existing = conn.execute("SELECT COUNT(*) FROM vocab_entry").fetchone()[0]
        inserted = 0
        for topic, words in C.VOCAB.items():
            for w in words:
                headword = w["word"]
                for lang in C.LANGUAGE_CODES:
                    translation = w["translations"].get(lang, "")
                    if not translation:
                        continue
                    eid = _eid(lang, headword, topic)
                    cur = conn.execute(
                        """INSERT OR IGNORE INTO vocab_entry
                           (id, language, headword, word, translation, definition,
                            pos, example, cefr, frequency, topic)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (eid, lang, headword, headword, translation, w["definition"],
                         w["pos"], w["example"], w["cefr"], int(w["frequency"]), topic))
                    inserted += cur.rowcount
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM vocab_entry").fetchone()[0]
        conn.close()
        return {"expanded": inserted, "total_entries": total, "was_empty": existing == 0}

    # ── Browsing ─────────────────────────────────────────────────────────────
    def list(self, language: str, topic: Optional[str] = None,
             level: Optional[str] = None, limit: int = 100) -> list[dict]:
        conn = _conn()
        q = "SELECT * FROM vocab_entry WHERE language=?"
        params: list = [language]
        if topic:
            q += " AND topic=?"
            params.append(topic)
        if level:
            q += " AND cefr=?"
            params.append(level)
        q += " ORDER BY frequency DESC, headword ASC LIMIT ?"
        params.append(limit)
        rows = conn.execute(q, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def topics(self, language: Optional[str] = None) -> list[dict]:
        conn = _conn()
        if language:
            rows = conn.execute(
                "SELECT topic, COUNT(*) c FROM vocab_entry WHERE language=? GROUP BY topic ORDER BY topic",
                (language,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT topic, COUNT(*) c FROM vocab_entry GROUP BY topic ORDER BY topic").fetchall()
        conn.close()
        return [{"topic": r["topic"], "count": r["c"],
                 "name": (C.topic_meta(r["topic"]) or {}).get("name", r["topic"])} for r in rows]

    def search(self, language: str, q: str, limit: int = 50) -> list[dict]:
        conn = _conn()
        like = f"%{q.lower()}%"
        rows = conn.execute(
            """SELECT * FROM vocab_entry WHERE language=?
               AND (LOWER(headword) LIKE ? OR LOWER(translation) LIKE ? OR LOWER(definition) LIKE ?)
               ORDER BY frequency DESC LIMIT ?""",
            (language, like, like, like, limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── SRS (SM-2) ───────────────────────────────────────────────────────────
    def _seed_cards(self, language: str, n: int = 20) -> int:
        """Create review cards for the most frequent words not yet carded."""
        conn = _conn()
        carded = {r["headword"] for r in conn.execute(
            "SELECT headword FROM vocab_review WHERE language=?", (language,)).fetchall()}
        rows = conn.execute(
            "SELECT DISTINCT headword, topic, frequency FROM vocab_entry WHERE language=? ORDER BY frequency DESC",
            (language,)).fetchall()
        created = 0
        for r in rows:
            if created >= n:
                break
            if r["headword"] in carded:
                continue
            cid = _eid(language, r["headword"], "review")
            conn.execute(
                """INSERT OR IGNORE INTO vocab_review
                   (card_id, language, headword, topic, due_date)
                   VALUES (?,?,?,?, date('now'))""",
                (cid, language, r["headword"], r["topic"]))
            carded.add(r["headword"])
            created += 1
        conn.commit()
        conn.close()
        return created

    def review(self, language: str, limit: int = 20) -> list[dict]:
        """Return cards due today; seed fresh cards from the bank if none are due."""
        conn = _conn()
        rows = conn.execute(
            "SELECT * FROM vocab_review WHERE language=? AND due_date<=date('now') ORDER BY due_date ASC LIMIT ?",
            (language, limit)).fetchall()
        conn.close()
        if not rows:
            self._seed_cards(language, max(limit, 20))
            conn = _conn()
            rows = conn.execute(
                "SELECT * FROM vocab_review WHERE language=? AND due_date<=date('now') ORDER BY due_date ASC LIMIT ?",
                (language, limit)).fetchall()
            conn.close()
        return [self._fmt_card(dict(r)) for r in rows]

    def _fmt_card(self, card: dict) -> dict:
        # attach a representative translation for the headword
        conn = _conn()
        row = conn.execute(
            "SELECT word, translation, definition, example, pos, cefr, topic FROM vocab_entry WHERE language=? AND headword=? LIMIT 1",
            (card["language"], card["headword"])).fetchone()
        conn.close()
        if row:
            card.update({"word": row["word"], "translation": row["translation"],
                         "definition": row["definition"], "example": row["example"],
                         "pos": row["pos"], "cefr": row["cefr"]})
        return card

    def grade(self, card_id: str, grade: int) -> dict:
        """Apply the SM-2 update. ``grade`` is 0..5 (>=3 is a pass)."""
        grade = max(0, min(5, int(grade)))
        conn = _conn()
        row = conn.execute("SELECT * FROM vocab_review WHERE card_id=?", (card_id,)).fetchone()
        if not row:
            conn.close()
            raise KeyError(f"card not found: {card_id}")
        card = dict(row)
        ease = card["ease"]
        interval = card["interval"]
        reps = card["reps"]

        # SM-2 ease update.
        ease = ease + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
        if ease < 1.3:
            ease = 1.3

        if grade < 3:
            # Failed recall — reset the repetition cycle.
            reps = 0
            interval = 1
        else:
            reps += 1
            if reps == 1:
                interval = 1
            elif reps == 2:
                interval = 6
            else:
                interval = int(round(interval * ease))
                if interval < 1:
                    interval = 1

        due = (date.today() + timedelta(days=interval)).isoformat()
        conn.execute(
            """UPDATE vocab_review SET ease=?, interval=?, reps=?, due_date=?, last_grade=?
               WHERE card_id=?""",
            (round(ease, 3), interval, reps, due, grade, card_id))
        conn.commit()
        conn.close()
        return {"card_id": card_id, "ease": round(ease, 3), "interval": interval,
                "reps": reps, "due_date": due, "grade": grade,
                "passed": grade >= 3}

    def stats(self) -> dict:
        conn = _conn()
        total = conn.execute("SELECT COUNT(*) FROM vocab_entry").fetchone()[0]
        by_lang = {r["language"]: r["c"] for r in conn.execute(
            "SELECT language, COUNT(*) c FROM vocab_entry GROUP BY language").fetchall()}
        topics = conn.execute("SELECT COUNT(DISTINCT topic) FROM vocab_entry").fetchone()[0]
        cards = conn.execute("SELECT COUNT(*) FROM vocab_review").fetchone()[0]
        due = conn.execute("SELECT COUNT(*) FROM vocab_review WHERE due_date<=date('now')").fetchone()[0]
        conn.close()
        return {"total_entries": total, "by_language": by_lang, "topics": topics,
                "review_cards": cards, "due_cards": due,
                "base_headwords": sum(len(v) for v in C.VOCAB.values())}


_instance: Optional[VocabularySystem] = None


def get_vocabulary_system() -> VocabularySystem:
    global _instance
    if _instance is None:
        _instance = VocabularySystem()
    return _instance
