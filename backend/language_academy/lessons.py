"""Lesson Engine — deterministic structured lessons for (language × level × topic).

The full catalog spans 7 languages × 6 levels × ~12 topics → hundreds of
lessons. Each lesson id is derived deterministically from its coordinates so
the same lesson is always reproducible (and cacheable). Generated lessons are
persisted; ``get`` regenerates on demand if a lesson is absent.
"""
from __future__ import annotations

import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Optional

from . import content as C

_DB = Path(".data/language_lessons.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS lesson (
            id TEXT PRIMARY KEY,
            language TEXT NOT NULL,
            level TEXT NOT NULL,
            topic TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_lesson_coords ON lesson(language, level, topic);
    """)
    return conn


def lesson_id(language: str, level: str, topic: str) -> str:
    return "lsn_" + hashlib.sha1(f"{language}:{level}:{topic}".encode()).hexdigest()[:14]


class LessonEngine:
    def __init__(self):
        _conn().close()

    # ── Generation ───────────────────────────────────────────────────────────
    def generate(self, language: str, level: str, topic: str, persist: bool = True) -> dict:
        if language not in C.LANGUAGE_CODES:
            raise ValueError(f"unknown language: {language}")
        if level not in C.LEVELS:
            raise ValueError(f"unknown level: {level}")
        if topic not in C.TOPIC_IDS:
            raise ValueError(f"unknown topic: {topic}")

        lid = lesson_id(language, level, topic)
        topic_name = (C.topic_meta(topic) or {}).get("name", topic)
        lang_name = next((l["name"] for l in C.LANGUAGES if l["code"] == language), language)
        title = f"{lang_name} {level}: {topic_name}"

        words = self._vocab(language, topic, level)
        grammar = self._grammar(language, level)
        reading = self._reading(words, topic_name)
        listening_script = self._listening_script(level)
        conversation = self._conversation(topic, language)
        exercises = self._exercises(words, grammar)
        assessment = self._assessment(words, grammar)

        lesson = {
            "id": lid,
            "title": title,
            "language": language,
            "level": level,
            "topic": topic,
            "objectives": [
                f"Learn key {topic_name.lower()} vocabulary in {lang_name}",
                f"Apply the grammar rule: {grammar['title']}" if grammar else "Reinforce core grammar",
                f"Practice a real {topic_name.lower()} conversation",
                "Complete reading, listening, and assessment tasks",
            ],
            "vocabulary": words,
            "grammar": grammar,
            "reading": reading,
            "listening_script": listening_script,
            "conversation_practice": conversation,
            "exercises": exercises,
            "assessment": assessment,
        }
        if persist:
            conn = _conn()
            conn.execute(
                "INSERT OR REPLACE INTO lesson (id, language, level, topic, title, body) VALUES (?,?,?,?,?,?)",
                (lid, language, level, topic, title, json.dumps(lesson)))
            conn.commit()
            conn.close()
        return lesson

    def _vocab(self, language: str, topic: str, level: str) -> list[dict]:
        words = C.VOCAB.get(topic, [])
        out = []
        for w in words:
            out.append({
                "word": w["word"],
                "pos": w["pos"],
                "definition": w["definition"],
                "example": w["example"],
                "cefr": w["cefr"],
                "translation": w["translations"].get(language, ""),
            })
        # Prefer words at-or-below the target level; keep order stable.
        order = {lvl: i for i, lvl in enumerate(C.LEVELS)}
        target = order.get(level, 0)
        at_level = [w for w in out if order.get(w["cefr"], 0) <= target]
        return at_level or out

    def _grammar(self, language: str, level: str) -> dict:
        # Pick the most relevant rule: language-specific at this level first,
        # then generic at this level, then any rule for the language.
        candidates = [r for r in C.GRAMMAR if r["level"] == level and r["language"] == language]
        if not candidates:
            candidates = [r for r in C.GRAMMAR if r["level"] == level and r["language"] == "generic"]
        if not candidates:
            candidates = [r for r in C.GRAMMAR if r["language"] in (language, "generic")]
        rule = candidates[0]
        return {"id": rule["id"], "title": rule["title"], "level": rule["level"],
                "explanation": rule["explanation"], "examples": rule["examples"],
                "common_mistakes": rule["common_mistakes"]}

    def _reading(self, words: list[dict], topic_name: str) -> dict:
        sample = words[:5]
        sentences = [w["example"] for w in sample if w.get("example")]
        passage = f"This short text is about {topic_name.lower()}. " + " ".join(sentences)
        glossary = [{"word": w["word"], "translation": w["translation"],
                     "definition": w["definition"]} for w in sample]
        return {"passage": passage, "glossary": glossary}

    def _listening_script(self, level: str) -> str:
        for ex in C.LISTENING:
            if ex["level"] == level:
                return ex["transcript"]
        # fall back to closest available level
        return C.LISTENING[0]["transcript"]

    def _conversation(self, topic: str, language: str) -> dict:
        # Map topic → a fitting scenario where possible.
        topic_to_scenario = {
            "food": "restaurant", "travel": "airport", "daily_life": "shopping",
            "business": "business_meeting", "finance": "shopping",
            "accounting": "accounting_meeting", "investing": "investment_pitch",
            "healthcare": "tax_consultation", "family": "date",
        }
        sid = topic_to_scenario.get(topic, "restaurant")
        scenario = next((s for s in C.CONVERSATION_SCENARIOS if s["id"] == sid),
                        C.CONVERSATION_SCENARIOS[0])
        return {"scenario": scenario["id"], "title": scenario["title"],
                "prompts": scenario["sample_prompts"], "target_vocab": scenario["target_vocab"]}

    def _exercises(self, words: list[dict], grammar: dict) -> list[dict]:
        ex: list[dict] = []
        # Fill-in-the-blank from example sentences.
        for w in words[:3]:
            example = w.get("example", "")
            if w["word"] in example:
                prompt = example.replace(w["word"], "_____", 1)
                ex.append({"type": "fill_in_blank", "prompt": prompt, "answer": w["word"]})
        # Matching (English → translation).
        if len(words) >= 3:
            pairs = [{"word": w["word"], "translation": w["translation"]} for w in words[:4]]
            ex.append({"type": "matching", "prompt": "Match each word to its translation.",
                       "pairs": pairs, "answer": {p["word"]: p["translation"] for p in pairs}})
        # Translation.
        for w in words[:2]:
            ex.append({"type": "translation", "prompt": f"Translate to the target language: '{w['word']}'",
                       "answer": w["translation"]})
        # Grammar correction (from a common mistake).
        if grammar and grammar.get("common_mistakes"):
            m = grammar["common_mistakes"][0]
            ex.append({"type": "correction", "prompt": f"Correct this: '{m['wrong']}'",
                       "answer": m["right"], "note": m["note"]})
        return ex

    def _assessment(self, words: list[dict], grammar: dict) -> dict:
        questions = []
        for w in words[:4]:
            distractors = [o["translation"] for o in words if o["word"] != w["word"]][:3]
            options = list(dict.fromkeys([w["translation"]] + distractors))
            questions.append({
                "q": f"What is the translation of '{w['word']}'?",
                "options": options,
                "answer": w["translation"],
            })
        if grammar and grammar.get("common_mistakes"):
            m = grammar["common_mistakes"][0]
            questions.append({
                "q": f"Which is correct?",
                "options": [m["right"], m["wrong"]],
                "answer": m["right"],
            })
        return {"questions": questions, "passing_score": 0.7}

    # ── Catalog / retrieval ──────────────────────────────────────────────────
    def _catalog_coords(self, language: Optional[str] = None, level: Optional[str] = None,
                        topic: Optional[str] = None) -> list[tuple[str, str, str]]:
        langs = [language] if language else C.LANGUAGE_CODES
        levels = [level] if level else C.LEVELS
        topics = [topic] if topic else C.TOPIC_IDS
        return [(lg, lv, tp) for lg in langs for lv in levels for tp in topics]

    def list(self, language: Optional[str] = None, level: Optional[str] = None,
             topic: Optional[str] = None, limit: int = 200) -> list[dict]:
        out = []
        for lg, lv, tp in self._catalog_coords(language, level, topic):
            topic_name = (C.topic_meta(tp) or {}).get("name", tp)
            lang_name = next((l["name"] for l in C.LANGUAGES if l["code"] == lg), lg)
            out.append({
                "id": lesson_id(lg, lv, tp),
                "title": f"{lang_name} {lv}: {topic_name}",
                "language": lg, "level": lv, "topic": tp,
                "topic_name": topic_name,
            })
            if len(out) >= limit:
                break
        return out

    def count(self) -> int:
        return len(self._catalog_coords())

    def get(self, lesson_id_: str) -> Optional[dict]:
        conn = _conn()
        row = conn.execute("SELECT body FROM lesson WHERE id=?", (lesson_id_,)).fetchone()
        conn.close()
        if row:
            return json.loads(row["body"])
        # Not persisted yet — find the coordinates that hash to this id and generate.
        for lg, lv, tp in self._catalog_coords():
            if lesson_id(lg, lv, tp) == lesson_id_:
                return self.generate(lg, lv, tp)
        return None

    def stats(self) -> dict:
        conn = _conn()
        generated = conn.execute("SELECT COUNT(*) FROM lesson").fetchone()[0]
        conn.close()
        return {"catalog_size": self.count(), "generated": generated,
                "languages": len(C.LANGUAGE_CODES), "levels": len(C.LEVELS),
                "topics": len(C.TOPIC_IDS)}


_instance: Optional[LessonEngine] = None


def get_lesson_engine() -> LessonEngine:
    global _instance
    if _instance is None:
        _instance = LessonEngine()
    return _instance
