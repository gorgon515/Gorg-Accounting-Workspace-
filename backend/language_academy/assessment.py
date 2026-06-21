"""Assessment System — placement tests, unit/level tests, weakness detection.

``placement`` builds a graded test spanning all CEFR levels; ``placement_grade``
estimates a CEFR level from the answers with a per-area breakdown. ``tests``
generates deterministic unit tests / level exams from the curriculum + vocab +
grammar; ``submit`` grades them and returns real weakness detection and study
recommendations (pointing back to lessons and grammar rules).
"""
from __future__ import annotations

import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Optional

from . import content as C

_DB = Path(".data/language_assessment.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS assessment_test (
            id TEXT PRIMARY KEY,
            language TEXT NOT NULL,
            level TEXT DEFAULT '',
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS assessment_result (
            id TEXT PRIMARY KEY,
            test_id TEXT NOT NULL,
            score REAL DEFAULT 0,
            passed INTEGER DEFAULT 0,
            detail TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


def _test_id(language: str, kind: str, key: str) -> str:
    return "tst_" + hashlib.sha1(f"{language}:{kind}:{key}".encode()).hexdigest()[:14]


def _vocab_question(language: str, w: dict, pool: list[dict]) -> dict:
    answer = w["translations"].get(language, "")
    distractors = [o["translations"].get(language, "") for o in pool
                   if o["word"] != w["word"] and o["translations"].get(language, "")][:3]
    options = list(dict.fromkeys([answer] + distractors))
    return {"area": "vocabulary", "cefr": w["cefr"],
            "q": f"What is '{w['word']}' in {language}?",
            "options": options, "answer": answer}


def _grammar_question(rule: dict) -> dict:
    m = rule["common_mistakes"][0]
    return {"area": "grammar", "cefr": rule["level"], "rule_id": rule["id"],
            "q": f"Which is correct? ({rule['title']})",
            "options": [m["right"], m["wrong"]], "answer": m["right"]}


class AssessmentSystem:
    def __init__(self):
        _conn().close()

    # ── Placement ────────────────────────────────────────────────────────────
    def placement(self, language: str) -> dict:
        if language not in C.LANGUAGE_CODES:
            raise ValueError(f"unknown language: {language}")
        questions = []
        # One or two vocab questions per CEFR level, drawn from words at that level.
        all_words = [w for words in C.VOCAB.values() for w in words]
        for level in C.LEVELS:
            level_words = [w for w in all_words if w["cefr"] == level and w["translations"].get(language)]
            for w in level_words[:2]:
                questions.append(_vocab_question(language, w, all_words))
        # Add a grammar question per tier where available.
        for level in ["A2", "B1", "B2", "C1"]:
            rule = next((r for r in C.GRAMMAR if r["level"] == level
                         and r["language"] in (language, "generic")), None)
            if rule:
                questions.append(_grammar_question(rule))
        tid = _test_id(language, "placement", "v1")
        title = f"{language.capitalize()} Placement Test"
        body = {"id": tid, "language": language, "kind": "placement",
                "title": title, "questions": questions}
        self._save_test(tid, language, "", "placement", title, body)
        # Serve without answers.
        served = {**body, "questions": [{k: v for k, v in q.items() if k != "answer"}
                                        for q in questions]}
        return served

    def placement_grade(self, language: str, answers: list) -> dict:
        body = self._load_test(_test_id(language, "placement", "v1"))
        if not body:
            body = self.placement(language)
            body = self._load_test(_test_id(language, "placement", "v1"))
        questions = body["questions"]
        per_level: dict[str, dict] = {lvl: {"correct": 0, "total": 0} for lvl in C.LEVELS}
        per_area: dict[str, dict] = {}
        correct = 0
        for i, q in enumerate(questions):
            given = answers[i] if i < len(answers) else None
            lvl = q.get("cefr", "A1")
            area = q.get("area", "general")
            per_level.setdefault(lvl, {"correct": 0, "total": 0})
            per_area.setdefault(area, {"correct": 0, "total": 0})
            per_level[lvl]["total"] += 1
            per_area[area]["total"] += 1
            if given == q.get("answer"):
                correct += 1
                per_level[lvl]["correct"] += 1
                per_area[area]["correct"] += 1

        # Estimate CEFR: highest level where the learner scored >= 50%.
        estimated = "A1"
        for lvl in C.LEVELS:
            d = per_level.get(lvl, {"correct": 0, "total": 0})
            if d["total"] and d["correct"] / d["total"] >= 0.5:
                estimated = lvl
        breakdown = {lvl: {"correct": d["correct"], "total": d["total"],
                           "pct": round(d["correct"] / d["total"], 3) if d["total"] else 0.0}
                     for lvl, d in per_level.items()}
        area_breakdown = {a: {"correct": d["correct"], "total": d["total"],
                              "pct": round(d["correct"] / d["total"], 3) if d["total"] else 0.0}
                          for a, d in per_area.items()}
        total = len(questions)
        return {
            "language": language,
            "estimated_level": estimated,
            "score": round(correct / total, 3) if total else 0.0,
            "correct": correct,
            "total": total,
            "per_level": breakdown,
            "per_area": area_breakdown,
            "recommendation": f"Start studying at level {estimated}.",
        }

    # ── Unit / level tests ───────────────────────────────────────────────────
    def _build_test(self, language: str, level: str, kind: str) -> dict:
        # kind: 'unit' (single topic at a level) or 'level' (whole level exam)
        topics = self._topics_for_level(level)
        questions = []
        for topic in topics:
            words = [w for w in C.VOCAB.get(topic, []) if w["translations"].get(language)]
            for w in words[:3]:
                questions.append({**_vocab_question(language, w, words), "topic": topic})
        rule = next((r for r in C.GRAMMAR if r["level"] == level
                     and r["language"] in (language, "generic")), None)
        if rule:
            questions.append({**_grammar_question(rule), "topic": "grammar"})
        key = f"{level}:{kind}"
        tid = _test_id(language, kind, key)
        title = f"{language.capitalize()} {level} {'Level Exam' if kind == 'level' else 'Unit Test'}"
        return {"id": tid, "language": language, "level": level, "kind": kind,
                "title": title, "questions": questions, "passing_score": 0.7}

    def _topics_for_level(self, level: str) -> list[str]:
        from .curriculum import Curriculum
        # reuse curriculum topic mapping
        topics = [t["id"] for t in Curriculum().level("spanish", level)["topics"]]
        return topics or [C.TOPIC_IDS[0]]

    def tests(self, language: Optional[str] = None, level: Optional[str] = None,
              kind: Optional[str] = None) -> list[dict]:
        langs = [language] if language else C.LANGUAGE_CODES
        levels = [level] if level else C.LEVELS
        kinds = [kind] if kind else ["unit", "level"]
        out = []
        for lg in langs:
            for lv in levels:
                for k in kinds:
                    test = self._build_test(lg, lv, k)
                    self._save_test(test["id"], lg, lv, k, test["title"], test)
                    out.append({"id": test["id"], "language": lg, "level": lv,
                                "kind": k, "title": test["title"],
                                "question_count": len(test["questions"])})
        return out

    def get_test(self, test_id: str) -> Optional[dict]:
        body = self._load_test(test_id)
        if not body:
            # Try to regenerate by scanning the deterministic id space.
            for lg in C.LANGUAGE_CODES:
                for lv in C.LEVELS:
                    for k in ("unit", "level"):
                        test = self._build_test(lg, lv, k)
                        if test["id"] == test_id:
                            self._save_test(test["id"], lg, lv, k, test["title"], test)
                            body = test
                            break
                    if body:
                        break
                if body:
                    break
        if not body:
            return None
        # Serve without answers.
        served = {**body, "questions": [{k: v for k, v in q.items() if k != "answer"}
                                        for q in body["questions"]]}
        return served

    def submit(self, test_id: str, answers: list) -> dict:
        body = self._load_test(test_id) or self._regenerate(test_id)
        if not body:
            raise KeyError(f"test not found: {test_id}")
        questions = body["questions"]
        per_topic: dict[str, dict] = {}
        per_area: dict[str, dict] = {}
        correct = 0
        for i, q in enumerate(questions):
            given = answers[i] if i < len(answers) else None
            topic = q.get("topic", q.get("area", "general"))
            area = q.get("area", "general")
            per_topic.setdefault(topic, {"correct": 0, "total": 0})
            per_area.setdefault(area, {"correct": 0, "total": 0})
            per_topic[topic]["total"] += 1
            per_area[area]["total"] += 1
            if given == q.get("answer"):
                correct += 1
                per_topic[topic]["correct"] += 1
                per_area[area]["correct"] += 1
        total = len(questions)
        score = round(correct / total, 3) if total else 0.0
        passed = score >= body.get("passing_score", 0.7)

        # Weakness detection — topics/areas scoring below 60%.
        weaknesses = []
        for topic, d in per_topic.items():
            pct = d["correct"] / d["total"] if d["total"] else 0.0
            if pct < 0.6:
                weaknesses.append({"topic": topic, "pct": round(pct, 3),
                                   "correct": d["correct"], "total": d["total"]})
        weaknesses.sort(key=lambda x: x["pct"])

        recommendations = self._recommendations(body, weaknesses)
        per_topic_out = {t: {"correct": d["correct"], "total": d["total"],
                             "pct": round(d["correct"] / d["total"], 3) if d["total"] else 0.0}
                         for t, d in per_topic.items()}

        result = {
            "test_id": test_id,
            "score": score,
            "passed": passed,
            "correct": correct,
            "total": total,
            "per_topic": per_topic_out,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
        }
        # Persist the result.
        rid = hashlib.sha1(f"{test_id}:{json.dumps(answers)}".encode()).hexdigest()[:16]
        conn = _conn()
        conn.execute(
            "INSERT OR REPLACE INTO assessment_result (id, test_id, score, passed, detail) VALUES (?,?,?,?,?)",
            (rid, test_id, score, int(passed), json.dumps(result)))
        conn.commit()
        conn.close()
        return result

    def _recommendations(self, body: dict, weaknesses: list[dict]) -> list[dict]:
        from .lessons import lesson_id
        language = body.get("language", "spanish")
        level = body.get("level", "A1")
        recs = []
        for w in weaknesses:
            topic = w["topic"]
            if topic in C.TOPIC_IDS:
                recs.append({
                    "topic": topic,
                    "action": f"Review the {language} {level} lesson on {(C.topic_meta(topic) or {}).get('name', topic)}.",
                    "lesson_id": lesson_id(language, level, topic),
                })
            elif topic in ("grammar",) or topic == "grammar":
                rule = next((r for r in C.GRAMMAR if r["level"] == level
                             and r["language"] in (language, "generic")), None)
                if rule:
                    recs.append({"topic": "grammar",
                                 "action": f"Revisit the grammar rule '{rule['title']}'.",
                                 "rule_id": rule["id"]})
        if not recs:
            recs.append({"topic": "general", "action": "Solid result — advance to the next level.",
                         "lesson_id": None})
        return recs

    # ── Persistence helpers ──────────────────────────────────────────────────
    def _save_test(self, tid, language, level, kind, title, body):
        conn = _conn()
        conn.execute(
            "INSERT OR REPLACE INTO assessment_test (id, language, level, kind, title, body) VALUES (?,?,?,?,?,?)",
            (tid, language, level, kind, title, json.dumps(body)))
        conn.commit()
        conn.close()

    def _load_test(self, test_id: str) -> Optional[dict]:
        conn = _conn()
        row = conn.execute("SELECT body FROM assessment_test WHERE id=?", (test_id,)).fetchone()
        conn.close()
        return json.loads(row["body"]) if row else None

    def _regenerate(self, test_id: str) -> Optional[dict]:
        for lg in C.LANGUAGE_CODES:
            for lv in C.LEVELS:
                for k in ("unit", "level"):
                    test = self._build_test(lg, lv, k)
                    if test["id"] == test_id:
                        self._save_test(test["id"], lg, lv, k, test["title"], test)
                        return test
        return None

    def stats(self) -> dict:
        conn = _conn()
        tests = conn.execute("SELECT COUNT(*) FROM assessment_test").fetchone()[0]
        results = conn.execute("SELECT COUNT(*) FROM assessment_result").fetchone()[0]
        conn.close()
        return {"generated_tests": tests, "submitted_results": results,
                "catalog_size": len(C.LANGUAGE_CODES) * len(C.LEVELS) * 2}


_instance: Optional[AssessmentSystem] = None


def get_assessment_system() -> AssessmentSystem:
    global _instance
    if _instance is None:
        _instance = AssessmentSystem()
    return _instance
