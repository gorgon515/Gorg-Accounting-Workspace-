import sqlite3
import uuid
import time
import json
import os
import threading
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "voice_os.db"

STT_ENGINES = ["whisper", "faster_whisper", "vosk", "system"]
TTS_ENGINES = ["piper", "coqui", "system"]


class VoiceOS:
    _instance = None

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._mode = "idle"  # idle / push_to_talk / always_listening
        self._stt_engine = "whisper"
        self._tts_engine = "system"
        self._active_profile: Optional[str] = None
        self._lock = threading.Lock()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS voice_profile (
                id TEXT PRIMARY KEY, name TEXT, stt_engine TEXT, tts_engine TEXT,
                voice_name TEXT, speed REAL DEFAULT 1.0, pitch REAL DEFAULT 1.0,
                language TEXT DEFAULT 'en', wake_word TEXT DEFAULT 'helios',
                created_at REAL, updated_at REAL, is_active INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS conversation_session (
                id TEXT PRIMARY KEY, profile_id TEXT, started_at REAL, ended_at REAL,
                turn_count INTEGER DEFAULT 0, summary TEXT
            );
            CREATE TABLE IF NOT EXISTS conversation_turn (
                id TEXT PRIMARY KEY, session_id TEXT, role TEXT, content TEXT,
                ts REAL, latency_ms REAL, engine TEXT
            );
            CREATE TABLE IF NOT EXISTS wake_event (
                id TEXT PRIMARY KEY, ts REAL, keyword TEXT, confidence REAL, profile_id TEXT
            );
            CREATE TABLE IF NOT EXISTS tts_cache (
                id TEXT PRIMARY KEY, text_hash TEXT UNIQUE, engine TEXT,
                voice TEXT, audio_path TEXT, duration_sec REAL, created_at REAL
            );
            """)

    # ── voice profiles ────────────────────────────────────────────────────
    def create_profile(self, name: str, stt_engine: str = "whisper",
                       tts_engine: str = "system", voice_name: str = "default",
                       wake_word: str = "helios", language: str = "en") -> dict:
        now = time.time()
        pid = str(uuid.uuid4())
        with sqlite3.connect(self._db) as c:
            c.execute("""INSERT INTO voice_profile VALUES (?,?,?,?,?,1.0,1.0,?,?,?,?,0)""",
                      (pid, name, stt_engine, tts_engine, voice_name, language, wake_word, now, now))
        return self.get_profile(pid)

    def list_profiles(self) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute("SELECT * FROM voice_profile ORDER BY created_at").fetchall()
        cols = ["id", "name", "stt_engine", "tts_engine", "voice_name", "speed", "pitch",
                "language", "wake_word", "created_at", "updated_at", "is_active"]
        return [dict(zip(cols, r)) for r in rows]

    def get_profile(self, pid: str) -> Optional[dict]:
        with sqlite3.connect(self._db) as c:
            row = c.execute("SELECT * FROM voice_profile WHERE id=?", (pid,)).fetchone()
        if not row:
            return None
        cols = ["id", "name", "stt_engine", "tts_engine", "voice_name", "speed", "pitch",
                "language", "wake_word", "created_at", "updated_at", "is_active"]
        return dict(zip(cols, row))

    def set_active_profile(self, pid: str) -> bool:
        with sqlite3.connect(self._db) as c:
            c.execute("UPDATE voice_profile SET is_active=0")
            n = c.execute("UPDATE voice_profile SET is_active=1, updated_at=? WHERE id=?",
                          (time.time(), pid)).rowcount
        if n:
            self._active_profile = pid
        return bool(n)

    def update_profile(self, pid: str, **fields) -> Optional[dict]:
        allowed = {"stt_engine", "tts_engine", "voice_name", "speed", "pitch",
                   "language", "wake_word", "name"}
        fields = {k: v for k, v in fields.items() if k in allowed}
        if not fields:
            return self.get_profile(pid)
        sets = ", ".join(f"{k}=?" for k in fields) + ", updated_at=?"
        with sqlite3.connect(self._db) as c:
            c.execute(f"UPDATE voice_profile SET {sets} WHERE id=?",
                      (*fields.values(), time.time(), pid))
        return self.get_profile(pid)

    # ── mode management ───────────────────────────────────────────────────
    def set_mode(self, mode: str) -> dict:
        if mode not in ("idle", "push_to_talk", "always_listening"):
            raise ValueError(f"Unknown mode: {mode}")
        with self._lock:
            self._mode = mode
        return {"mode": mode, "ts": time.time()}

    def get_mode(self) -> dict:
        return {"mode": self._mode, "stt_engine": self._stt_engine,
                "tts_engine": self._tts_engine, "active_profile": self._active_profile}

    def set_stt_engine(self, engine: str) -> dict:
        if engine not in STT_ENGINES:
            raise ValueError(f"Unknown STT engine: {engine}")
        self._stt_engine = engine
        return {"stt_engine": engine}

    def set_tts_engine(self, engine: str) -> dict:
        if engine not in TTS_ENGINES:
            raise ValueError(f"Unknown TTS engine: {engine}")
        self._tts_engine = engine
        return {"tts_engine": engine}

    # ── wake word events ──────────────────────────────────────────────────
    def record_wake_event(self, keyword: str = "helios", confidence: float = 1.0) -> dict:
        eid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute("INSERT INTO wake_event VALUES (?,?,?,?,?)",
                      (eid, now, keyword, confidence, self._active_profile))
        return {"id": eid, "ts": now, "keyword": keyword, "confidence": confidence}

    def wake_history(self, limit: int = 50) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute("SELECT * FROM wake_event ORDER BY ts DESC LIMIT ?",
                             (limit,)).fetchall()
        cols = ["id", "ts", "keyword", "confidence", "profile_id"]
        return [dict(zip(cols, r)) for r in rows]

    # ── conversation sessions ─────────────────────────────────────────────
    def start_session(self, profile_id: str = "") -> dict:
        sid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute("INSERT INTO conversation_session VALUES (?,?,?,NULL,0,NULL)",
                      (sid, profile_id or self._active_profile or "", now))
        return {"id": sid, "started_at": now, "turns": []}

    def end_session(self, sid: str, summary: str = "") -> Optional[dict]:
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute("UPDATE conversation_session SET ended_at=?, summary=? WHERE id=?",
                      (now, summary, sid))
            row = c.execute("SELECT * FROM conversation_session WHERE id=?", (sid,)).fetchone()
        if not row:
            return None
        cols = ["id", "profile_id", "started_at", "ended_at", "turn_count", "summary"]
        return dict(zip(cols, row))

    def add_turn(self, session_id: str, role: str, content: str,
                 latency_ms: float = 0, engine: str = "") -> dict:
        tid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute("INSERT INTO conversation_turn VALUES (?,?,?,?,?,?,?)",
                      (tid, session_id, role, content, now, latency_ms, engine))
            c.execute("UPDATE conversation_session SET turn_count=turn_count+1 WHERE id=?",
                      (session_id,))
        return {"id": tid, "session_id": session_id, "role": role, "content": content,
                "ts": now, "latency_ms": latency_ms}

    def get_session(self, sid: str) -> Optional[dict]:
        with sqlite3.connect(self._db) as c:
            row = c.execute("SELECT * FROM conversation_session WHERE id=?", (sid,)).fetchone()
            if not row:
                return None
            cols = ["id", "profile_id", "started_at", "ended_at", "turn_count", "summary"]
            s = dict(zip(cols, row))
            turns = c.execute(
                "SELECT * FROM conversation_turn WHERE session_id=? ORDER BY ts",
                (sid,)
            ).fetchall()
        tcols = ["id", "session_id", "role", "content", "ts", "latency_ms", "engine"]
        s["turns"] = [dict(zip(tcols, t)) for t in turns]
        return s

    def list_sessions(self, limit: int = 20) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT * FROM conversation_session ORDER BY started_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        cols = ["id", "profile_id", "started_at", "ended_at", "turn_count", "summary"]
        return [dict(zip(cols, r)) for r in rows]

    # ── TTS simulation ────────────────────────────────────────────────────
    def synthesize(self, text: str, voice: str = "", engine: str = "") -> dict:
        engine = engine or self._tts_engine
        estimated_sec = len(text.split()) * 0.4  # ~150 wpm
        return {"engine": engine, "voice": voice or "default",
                "text_length": len(text), "estimated_duration_sec": round(estimated_sec, 2),
                "status": "synthesized", "ts": time.time()}

    # ── STT simulation ────────────────────────────────────────────────────
    def transcribe(self, audio_path: str = "", text_input: str = "", engine: str = "") -> dict:
        engine = engine or self._stt_engine
        return {"engine": engine, "text": text_input or "[audio transcription]",
                "confidence": 0.97, "latency_ms": 320, "ts": time.time()}

    # ── capabilities ──────────────────────────────────────────────────────
    def capabilities(self) -> dict:
        return {
            "stt_engines": STT_ENGINES,
            "tts_engines": TTS_ENGINES,
            "modes": ["idle", "push_to_talk", "always_listening"],
            "wake_words": ["helios", "hey helios", "ok helios"],
            "languages": ["en", "es", "fr", "de", "ja", "zh"],
        }

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            profiles = c.execute("SELECT COUNT(*) FROM voice_profile").fetchone()[0]
            sessions = c.execute("SELECT COUNT(*) FROM conversation_session").fetchone()[0]
            turns = c.execute("SELECT COUNT(*) FROM conversation_turn").fetchone()[0]
            wake = c.execute("SELECT COUNT(*) FROM wake_event").fetchone()[0]
        return {"profiles": profiles, "sessions": sessions, "turns": turns,
                "wake_events": wake, "mode": self._mode,
                "stt_engine": self._stt_engine, "tts_engine": self._tts_engine}


_instance: Optional[VoiceOS] = None


def get_voice_os() -> VoiceOS:
    global _instance
    if _instance is None:
        _instance = VoiceOS()
    return _instance
