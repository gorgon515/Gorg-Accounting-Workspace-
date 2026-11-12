"""SQLite storage, field encryption and a hash-chained audit log."""
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

try:
    from cryptography.fernet import Fernet
except ImportError:  # pragma: no cover
    Fernet = None

DATA_DIR = Path(os.environ.get("CAREER_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
KEY_FILE = Path(os.environ.get("CAREER_KEY_FILE", Path.home() / ".config" / "career-agent" / "key"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile(section TEXT PRIMARY KEY, value BLOB NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(
  id INTEGER PRIMARY KEY, source TEXT NOT NULL, source_id TEXT, employer TEXT NOT NULL, title TEXT NOT NULL,
  location TEXT, arrangement TEXT, url TEXT NOT NULL, description TEXT, industry TEXT,
  comp_min REAL, comp_max REAL, comp_currency TEXT, mandatory TEXT, preferred TEXT,
  discovered_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, closed_at TEXT, desc_hash TEXT,
  fingerprint TEXT NOT NULL UNIQUE, score REAL, score_detail TEXT, classification TEXT, verified INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS applications(
  id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL UNIQUE REFERENCES jobs(id), status TEXT NOT NULL,
  date_applied TEXT, confirmation TEXT, resume_doc_id INTEGER, cover_doc_id INTEGER,
  recruiter TEXT, hiring_manager TEXT, next_action TEXT, next_action_due TEXT, outcome TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL, ts TEXT NOT NULL,
  kind TEXT NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS communications(id INTEGER PRIMARY KEY, application_id INTEGER, ts TEXT NOT NULL,
  direction TEXT NOT NULL, channel TEXT NOT NULL, counterpart TEXT, subject TEXT, body BLOB,
  classification TEXT, external_id TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS interviews(id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL, scheduled_at TEXT,
  stage TEXT, interviewer TEXT, prep_doc_id INTEGER, feedback TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL,
  version INTEGER NOT NULL, parent_id INTEGER, application_id INTEGER, content BLOB NOT NULL,
  sha256 TEXT NOT NULL, fact_check TEXT, approved INTEGER DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS achievements(id INTEGER PRIMARY KEY, text TEXT NOT NULL, context TEXT, evidence TEXT,
  tags TEXT, verified INTEGER DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS skills(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, category TEXT, level TEXT,
  verified INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY, ts TEXT NOT NULL, kind TEXT NOT NULL,
  application_id INTEGER, question TEXT NOT NULL, context TEXT, status TEXT NOT NULL DEFAULT 'pending',
  answer TEXT, resolved_at TEXT);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, ts TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  target TEXT, detail TEXT, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fernet():
    if Fernet is None:
        raise RuntimeError("cryptography is required for encrypted storage: pip install cryptography")
    key = os.environ.get("CAREER_KEY")
    if not key:
        if not KEY_FILE.exists():
            KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
            KEY_FILE.write_bytes(Fernet.generate_key())
            KEY_FILE.chmod(0o600)
        key = KEY_FILE.read_bytes().strip()
    return Fernet(key)


def encrypt(obj) -> bytes:
    return _fernet().encrypt(json.dumps(obj).encode())


def decrypt(blob):
    return json.loads(_fernet().decrypt(bytes(blob)).decode())


def connect(path=None) -> sqlite3.Connection:
    path = Path(path) if path else DATA_DIR / "career.db"
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    if str(path) != ":memory:":
        os.chmod(path, 0o600)
    return conn


def audit(conn, action, target=None, detail=None, actor="agent"):
    """Append-only, hash-chained record of every action taken on the user's behalf."""
    row = conn.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
    prev = row["hash"] if row else "0" * 64
    ts = now()
    payload = json.dumps([ts, actor, action, target, detail, prev], sort_keys=True, default=str)
    h = hashlib.sha256(payload.encode()).hexdigest()
    conn.execute("INSERT INTO audit(ts,actor,action,target,detail,prev_hash,hash) VALUES(?,?,?,?,?,?,?)",
                 (ts, actor, action, target, json.dumps(detail, default=str), prev, h))
    conn.commit()


def verify_audit(conn) -> bool:
    prev = "0" * 64
    for r in conn.execute("SELECT * FROM audit ORDER BY id"):
        payload = json.dumps([r["ts"], r["actor"], r["action"], r["target"], json.loads(r["detail"]), prev],
                             sort_keys=True, default=str)
        if r["prev_hash"] != prev or hashlib.sha256(payload.encode()).hexdigest() != r["hash"]:
            return False
        prev = r["hash"]
    return True


def get_setting(conn, key, default=None):
    r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return json.loads(r["value"]) if r else default


def set_setting(conn, key, value, actor="user"):
    conn.execute("INSERT INTO settings(key,value,updated_at) VALUES(?,?,?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                 (key, json.dumps(value), now()))
    audit(conn, "setting.set", key, value, actor)


ENCRYPTED = {"profile": ["value"], "communications": ["body"], "documents": ["content"]}
TABLES = ["profile", "settings", "jobs", "applications", "events", "communications", "interviews", "documents",
          "achievements", "skills", "approvals", "audit"]


def export_all(conn) -> dict:
    """Plain-JSON snapshot of every table (encrypted columns are decrypted). Protect the output yourself."""
    out = {}
    for t in TABLES:
        rows = []
        for r in conn.execute(f"SELECT * FROM {t}"):
            d = dict(r)
            for c in ENCRYPTED.get(t, []):
                if d[c] is not None:
                    d[c] = decrypt(d[c])
            rows.append(d)
        out[t] = rows
    return {"version": 1, "exported_at": now(), "tables": out}


def import_all(conn, snapshot: dict):
    """Restore a snapshot into an empty database, re-encrypting with this machine's key."""
    if conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0] or conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]:
        raise ValueError("refusing to import over a non-empty database")
    conn.execute("PRAGMA foreign_keys=OFF")
    for t in TABLES:
        conn.execute(f"DELETE FROM {t}")
        for d in snapshot["tables"].get(t, []):
            for c in ENCRYPTED.get(t, []):
                if d[c] is not None:
                    d[c] = encrypt(d[c])
            cols = list(d)
            conn.execute(f"INSERT INTO {t}({','.join(cols)}) VALUES({','.join('?' * len(cols))})", [d[c] for c in cols])
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")
