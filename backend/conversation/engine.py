"""
Real-time conversation engine with context tracking, multi-turn state,
multi-agent participation, and conversation analytics.
SQLite persistence at ~/.helios/conversation.db.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "conversation.db"


class ConversationEngine:

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS thread (
                id TEXT PRIMARY KEY,
                title TEXT,
                mode TEXT DEFAULT 'chat',
                status TEXT DEFAULT 'open',
                participants_json TEXT DEFAULT '[]',
                created_at REAL,
                updated_at REAL,
                summary TEXT,
                turn_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS message (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                role TEXT,
                content TEXT,
                agent_id TEXT,
                metadata_json TEXT DEFAULT '{}',
                ts REAL,
                tokens_est INTEGER DEFAULT 0
            );
            """)

    # ── threads ───────────────────────────────────────────────────────────
    def create_thread(self, title: str = "", mode: str = "chat",
                      participants: list = None) -> dict:
        tid = str(uuid.uuid4())
        now = time.time()
        participants = participants or []
        if mode not in ("chat", "voice", "multi_agent", "briefing"):
            mode = "chat"
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO thread VALUES (?,?,?,?,?,?,?,?,?)",
                (tid, title or f"Thread {tid[:8]}", mode, "open",
                 json.dumps(participants), now, now, None, 0)
            )
        return self.get_thread(tid)

    def send_message(self, thread_id: str, role: str = "user", content: str = "",
                     agent_id: str = "", metadata: dict = None) -> dict:
        mid = str(uuid.uuid4())
        now = time.time()
        if role not in ("user", "assistant", "agent", "system"):
            role = "user"
        tokens_est = max(1, len(content.split()))
        metadata = metadata or {}
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO message VALUES (?,?,?,?,?,?,?,?)",
                (mid, thread_id, role, content, agent_id or "",
                 json.dumps(metadata), now, tokens_est)
            )
            c.execute(
                "UPDATE thread SET turn_count=turn_count+1, updated_at=? WHERE id=?",
                (now, thread_id)
            )
        return {"id": mid, "thread_id": thread_id, "role": role, "content": content,
                "agent_id": agent_id, "metadata": metadata, "ts": now,
                "tokens_est": tokens_est}

    def get_thread(self, tid: str) -> Optional[dict]:
        with sqlite3.connect(self._db) as c:
            row = c.execute("SELECT * FROM thread WHERE id=?", (tid,)).fetchone()
            if not row:
                return None
            cols = ["id", "title", "mode", "status", "participants_json",
                    "created_at", "updated_at", "summary", "turn_count"]
            t = dict(zip(cols, row))
            try:
                t["participants"] = json.loads(t.pop("participants_json") or "[]")
            except Exception:
                t["participants"] = []
            msgs = c.execute(
                "SELECT * FROM message WHERE thread_id=? ORDER BY ts",
                (tid,)
            ).fetchall()
        mcols = ["id", "thread_id", "role", "content", "agent_id",
                 "metadata_json", "ts", "tokens_est"]
        messages = []
        for m in msgs:
            md = dict(zip(mcols, m))
            try:
                md["metadata"] = json.loads(md.pop("metadata_json") or "{}")
            except Exception:
                md["metadata"] = {}
            messages.append(md)
        t["messages"] = messages
        return t

    def list_threads(self, status: str = "", limit: int = 20) -> list:
        with sqlite3.connect(self._db) as c:
            if status:
                rows = c.execute(
                    "SELECT * FROM thread WHERE status=? ORDER BY updated_at DESC LIMIT ?",
                    (status, limit)
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM thread ORDER BY updated_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        cols = ["id", "title", "mode", "status", "participants_json",
                "created_at", "updated_at", "summary", "turn_count"]
        result = []
        for r in rows:
            d = dict(zip(cols, r))
            try:
                d["participants"] = json.loads(d.pop("participants_json") or "[]")
            except Exception:
                d["participants"] = []
            result.append(d)
        return result

    def close_thread(self, tid: str, summary: str = "") -> Optional[dict]:
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE thread SET status='closed', summary=?, updated_at=? WHERE id=?",
                (summary, now, tid)
            )
        return self.get_thread(tid)

    def get_context(self, tid: str, max_turns: int = 10) -> list:
        """Return recent turns formatted for LLM context."""
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                """SELECT role, content, agent_id, ts FROM message
                   WHERE thread_id=? ORDER BY ts DESC LIMIT ?""",
                (tid, max_turns)
            ).fetchall()
        turns = [{"role": r[0], "content": r[1], "agent_id": r[2], "ts": r[3]}
                 for r in reversed(rows)]
        return turns

    def summarize_thread(self, tid: str) -> dict:
        """Extract key points from user messages and return summary dict."""
        thread = self.get_thread(tid)
        if not thread:
            return {"error": "Thread not found"}
        messages = thread.get("messages", [])
        key_points = []
        participants = set()
        for m in messages:
            if m["role"] == "user":
                snippet = m["content"][:60]
                if snippet:
                    key_points.append(snippet)
            if m.get("agent_id"):
                participants.add(m["agent_id"])
        return {
            "thread_id": tid,
            "key_points": key_points,
            "turn_count": thread.get("turn_count", 0),
            "participants": list(participants),
            "mode": thread.get("mode", "chat"),
        }

    def search_threads(self, query: str) -> list:
        """Search threads by title or message content."""
        q = f"%{query}%"
        with sqlite3.connect(self._db) as c:
            # Search by title
            title_rows = c.execute(
                "SELECT id FROM thread WHERE title LIKE ? ORDER BY updated_at DESC LIMIT 20",
                (q,)
            ).fetchall()
            # Search by message content
            msg_rows = c.execute(
                """SELECT DISTINCT thread_id FROM message WHERE content LIKE ?
                   ORDER BY ts DESC LIMIT 20""",
                (q,)
            ).fetchall()
        seen = set()
        results = []
        for row in title_rows:
            tid = row[0]
            if tid not in seen:
                seen.add(tid)
                t = self.get_thread(tid)
                if t:
                    results.append(t)
        for row in msg_rows:
            tid = row[0]
            if tid not in seen:
                seen.add(tid)
                t = self.get_thread(tid)
                if t:
                    results.append(t)
        return results

    def analytics(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total_threads = c.execute("SELECT COUNT(*) FROM thread").fetchone()[0]
            total_messages = c.execute("SELECT COUNT(*) FROM message").fetchone()[0]
            active_threads = c.execute(
                "SELECT COUNT(*) FROM thread WHERE status='open'"
            ).fetchone()[0]
            avg_turns_row = c.execute(
                "SELECT AVG(turn_count) FROM thread WHERE turn_count > 0"
            ).fetchone()[0]
            avg_turns = round(avg_turns_row or 0.0, 2)
            by_mode = {}
            mode_rows = c.execute(
                "SELECT mode, COUNT(*) FROM thread GROUP BY mode"
            ).fetchall()
            for mode, cnt in mode_rows:
                by_mode[mode] = cnt
        return {
            "total_threads": total_threads,
            "total_messages": total_messages,
            "active_threads": active_threads,
            "avg_turns_per_thread": avg_turns,
            "threads_by_mode": by_mode,
        }

    def stats(self) -> dict:
        return self.analytics()


_instance: Optional[ConversationEngine] = None


def get_conversation_engine() -> ConversationEngine:
    global _instance
    if _instance is None:
        _instance = ConversationEngine()
    return _instance
