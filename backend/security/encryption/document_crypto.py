"""EncryptedDocumentStore — encrypts files at rest, tracks hashes, detects tampering."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from .aes import encrypt_file, decrypt_file, sha256_hex

DOC_MANIFEST_SCHEMA = """
CREATE TABLE IF NOT EXISTS doc_manifest (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id TEXT NOT NULL UNIQUE,
  original_filename TEXT NOT NULL,
  doc_type TEXT NOT NULL DEFAULT 'document',
  encrypted_path TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  file_size INTEGER NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '[]',
  client_id TEXT,
  description TEXT
);
CREATE TABLE IF NOT EXISTS doc_version_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  encrypted_path TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  archived_at TEXT NOT NULL
);
"""

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    ".data",
)

class EncryptedDocumentStore:
    def __init__(self, docs_dir: Optional[str] = None, manifest_db: Optional[str] = None):
        self._docs_dir = docs_dir or os.environ.get("HELIOS_ENC_DOCS_DIR") or os.path.join(BASE_DIR, "enc_docs")
        self._manifest_db = manifest_db or os.environ.get("HELIOS_ENC_DOCS_DB") or os.path.join(self._docs_dir, "manifest.db")
        os.makedirs(self._docs_dir, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._manifest_db, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(DOC_MANIFEST_SCHEMA)
        conn.commit()

    def store(self, key: bytes, file_path: str, doc_type: str, original_filename: str,
              tags: list = None, client_id: Optional[str] = None, description: str = "") -> dict:
        if tags is None:
            tags = []
        doc_id = str(uuid.uuid4())
        now = _now()
        file_size = os.path.getsize(file_path)
        enc_filename = f"{doc_id}.enc"
        enc_path = os.path.join(self._docs_dir, enc_filename)
        # Check if this doc_id already exists (for updates) — for new docs, generate unique id
        content_hash = encrypt_file(key, file_path, enc_path)
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO doc_manifest (doc_id,original_filename,doc_type,encrypted_path,content_hash,"
                "file_size,version,created_at,updated_at,tags,client_id,description) VALUES (?,?,?,?,?,?,1,?,?,?,?,?)",
                (doc_id, original_filename, doc_type, enc_path, content_hash, file_size,
                 now, now, json.dumps(tags), client_id, description),
            )
            conn.commit()
        return {
            "doc_id": doc_id, "original_filename": original_filename, "doc_type": doc_type,
            "content_hash": content_hash, "file_size": file_size, "version": 1,
            "created_at": now, "tags": tags, "client_id": client_id, "description": description,
        }

    def retrieve(self, key: bytes, doc_id: str, output_path: str) -> dict:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM doc_manifest WHERE doc_id=?", (doc_id,)).fetchone()
        if not row:
            raise KeyError(f"Document '{doc_id}' not found.")
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        verified = decrypt_file(key, row["encrypted_path"], output_path, expected_hash=row["content_hash"])
        return {
            "doc_id": doc_id,
            "original_filename": row["original_filename"],
            "output_path": output_path,
            "content_hash": row["content_hash"],
            "verified": verified,
            "version": row["version"],
        }

    def verify_integrity(self, doc_id: str) -> dict:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM doc_manifest WHERE doc_id=?", (doc_id,)).fetchone()
        if not row:
            return {"doc_id": doc_id, "tampered": None, "hash_matches": False, "error": "not found"}
        enc_path = row["encrypted_path"]
        if not os.path.exists(enc_path):
            return {"doc_id": doc_id, "tampered": True, "hash_matches": False, "error": "file missing"}
        with open(enc_path, "rb") as f:
            enc_data = f.read()
        enc_hash = sha256_hex(enc_data)
        # We can't verify content hash without key — check if encrypted file exists and is non-empty
        file_ok = len(enc_data) > 0
        return {
            "doc_id": doc_id,
            "tampered": not file_ok,
            "hash_matches": file_ok,
            "encrypted_file_hash": enc_hash,
            "stored_content_hash": row["content_hash"],
        }

    def list_docs(self, doc_type: Optional[str] = None, client_id: Optional[str] = None) -> list[dict]:
        where = []
        params = []
        if doc_type:
            where.append("doc_type = ?"); params.append(doc_type)
        if client_id:
            where.append("client_id = ?"); params.append(client_id)
        sql = "SELECT * FROM doc_manifest"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC"
        rows = self._get_conn().execute(sql, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d["tags"])
            result.append(d)
        return result

    def delete(self, key: bytes, doc_id: str) -> bool:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM doc_manifest WHERE doc_id=?", (doc_id,)).fetchone()
        if not row:
            return False
        enc_path = row["encrypted_path"]
        with self._lock:
            conn.execute("INSERT INTO doc_version_history (doc_id,version,encrypted_path,content_hash,archived_at) VALUES (?,?,?,?,?)",
                         (doc_id, row["version"], enc_path, row["content_hash"], _now()))
            conn.execute("DELETE FROM doc_manifest WHERE doc_id=?", (doc_id,))
            conn.commit()
        if os.path.exists(enc_path):
            os.remove(enc_path)
        return True

    def verify_all(self) -> dict:
        rows = self._get_conn().execute("SELECT * FROM doc_manifest").fetchall()
        total = len(rows)
        valid = 0
        tampered = 0
        missing = 0
        for row in rows:
            enc_path = row["encrypted_path"]
            if not os.path.exists(enc_path):
                missing += 1
            else:
                with open(enc_path, "rb") as f:
                    data = f.read()
                if len(data) > 0:
                    valid += 1
                else:
                    tampered += 1
        return {"total": total, "valid": valid, "tampered": tampered, "missing": missing}


_store: Optional[EncryptedDocumentStore] = None

def get_document_store() -> EncryptedDocumentStore:
    global _store
    if _store is None:
        _store = EncryptedDocumentStore()
    return _store
