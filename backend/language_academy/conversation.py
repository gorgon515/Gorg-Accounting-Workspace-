"""Conversation Simulator — stateful role-play sessions.

``start`` opens a session for a scenario and returns an opening line in the
target language. ``respond`` records each user turn and deterministically
advances through the scenario's sample prompts, returning the next AI line plus
lightweight feedback (length / target-vocab usage) and grammar corrections
(reusing the Grammar Academy's checker).
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

from . import content as C

_DB = Path(".data/language_conversation.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conv_session (
            id TEXT PRIMARY KEY,
            language TEXT NOT NULL,
            scenario TEXT NOT NULL,
            level TEXT DEFAULT 'A2',
            turn INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS conv_turn (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            speaker TEXT NOT NULL,
            text TEXT NOT NULL,
            feedback TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_turn_session ON conv_turn(session_id);
    """)
    return conn


# Greeting opening lines in the target language, keyed by language code.
_OPENINGS = {
    "spanish": "¡Hola! Bienvenido. ",
    "french": "Bonjour ! Bienvenue. ",
    "german": "Hallo! Willkommen. ",
    "italian": "Ciao! Benvenuto. ",
    "russian": "Privet! Dobro pozhalovat. ",
    "japanese": "Konnichiwa! Youkoso. ",
    "mandarin": "Nihao! Huanying. ",
}


class ConversationSimulator:
    def __init__(self):
        _conn().close()

    def scenarios(self) -> list[dict]:
        return [dict(s) for s in C.CONVERSATION_SCENARIOS]

    def _scenario(self, scenario_id: str) -> Optional[dict]:
        return next((s for s in C.CONVERSATION_SCENARIOS if s["id"] == scenario_id), None)

    def start(self, language: str, scenario: str, level: str = "A2") -> dict:
        if language not in C.LANGUAGE_CODES:
            raise ValueError(f"unknown language: {language}")
        sc = self._scenario(scenario)
        if not sc:
            raise ValueError(f"unknown scenario: {scenario}")
        sid = str(uuid.uuid4())
        opening_en = sc["sample_prompts"][0]
        opening = _OPENINGS.get(language, "") + opening_en
        conn = _conn()
        conn.execute(
            "INSERT INTO conv_session (id, language, scenario, level, turn) VALUES (?,?,?,?,0)",
            (sid, language, scenario, level))
        conn.execute(
            "INSERT INTO conv_turn (id, session_id, speaker, text) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), sid, "ai", opening))
        conn.commit()
        conn.close()
        return {
            "session_id": sid,
            "scenario": scenario,
            "title": sc["title"],
            "opening_line": opening,
            "instructions": f"You are the {sc['roles']['user']}. {sc['setup']} Respond in {language}.",
            "target_vocab": sc["target_vocab"],
            "roles": sc["roles"],
        }

    def respond(self, session_id: str, text: str) -> dict:
        conn = _conn()
        sess = conn.execute("SELECT * FROM conv_session WHERE id=?", (session_id,)).fetchone()
        if not sess:
            conn.close()
            raise KeyError(f"session not found: {session_id}")
        sess = dict(sess)
        sc = self._scenario(sess["scenario"])
        turn = sess["turn"] + 1

        # Record the user turn.
        feedback = self._feedback(text, sc)
        corrections = self._corrections(sess["language"], text)
        conn.execute(
            "INSERT INTO conv_turn (id, session_id, speaker, text, feedback) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), session_id, "user", text, json.dumps(feedback)))

        # Advance AI line through the scenario prompts.
        prompts = sc["sample_prompts"]
        done = turn >= len(prompts) - 1
        ai_index = min(turn, len(prompts) - 1)
        ai_line = _OPENINGS.get(sess["language"], "") + prompts[ai_index] if not done else "Thank you, that's all for now!"
        conn.execute(
            "INSERT INTO conv_turn (id, session_id, speaker, text) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), session_id, "ai", ai_line))
        status = "complete" if done else "active"
        conn.execute("UPDATE conv_session SET turn=?, status=? WHERE id=?", (turn, status, session_id))
        conn.commit()
        conn.close()
        return {
            "session_id": session_id,
            "turn": turn,
            "ai_response": ai_line,
            "feedback": feedback,
            "corrections": corrections,
            "status": status,
            "complete": done,
        }

    def _feedback(self, text: str, scenario: Optional[dict]) -> dict:
        tokens = text.split()
        n = len(tokens)
        lowered = text.lower()
        used = []
        if scenario:
            used = [v for v in scenario.get("target_vocab", []) if v.lower() in lowered]
        length_ok = n >= 3
        score = min(100, 40 + n * 5 + len(used) * 15)
        notes = []
        if not length_ok:
            notes.append("Try to respond in a full sentence.")
        if used:
            notes.append(f"Nice use of target vocabulary: {', '.join(used)}.")
        else:
            notes.append("Try to use some of the target vocabulary.")
        return {"length": n, "target_vocab_used": used, "score": min(100, score),
                "notes": notes}

    def _corrections(self, language: str, text: str) -> dict:
        from .grammar import get_grammar_academy
        return get_grammar_academy().check(language, text)

    def history(self, session_id: str) -> dict:
        conn = _conn()
        sess = conn.execute("SELECT * FROM conv_session WHERE id=?", (session_id,)).fetchone()
        if not sess:
            conn.close()
            raise KeyError(f"session not found: {session_id}")
        turns = conn.execute(
            "SELECT speaker, text, feedback, created_at FROM conv_turn WHERE session_id=? ORDER BY created_at ASC",
            (session_id,)).fetchall()
        conn.close()
        out_turns = []
        for t in turns:
            d = dict(t)
            try:
                d["feedback"] = json.loads(d["feedback"])
            except Exception:
                d["feedback"] = {}
            out_turns.append(d)
        return {"session": dict(sess), "turns": out_turns}

    def stats(self) -> dict:
        conn = _conn()
        sessions = conn.execute("SELECT COUNT(*) FROM conv_session").fetchone()[0]
        turns = conn.execute("SELECT COUNT(*) FROM conv_turn").fetchone()[0]
        conn.close()
        return {"sessions": sessions, "turns": turns,
                "scenarios": len(C.CONVERSATION_SCENARIOS)}


_instance: Optional[ConversationSimulator] = None


def get_conversation_simulator() -> ConversationSimulator:
    global _instance
    if _instance is None:
        _instance = ConversationSimulator()
    return _instance
