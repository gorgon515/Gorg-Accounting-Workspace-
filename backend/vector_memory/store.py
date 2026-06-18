"""
Vector Memory System backed by ChromaDB (local persistent).
Supports namespaced collections, metadata filtering, versioning, and pruning.
"""
import uuid
import sqlite3
import time
from pathlib import Path
from typing import Optional, Any

_CHROMA_DIR = Path(".data/chroma")
_META_DB = Path(".data/vector_memory.db")


def _meta_conn() -> sqlite3.Connection:
    _META_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_META_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vm_collection (
            name TEXT PRIMARY KEY,
            namespace TEXT NOT NULL DEFAULT 'default',
            description TEXT,
            doc_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vm_document (
            id TEXT PRIMARY KEY,
            collection TEXT NOT NULL,
            namespace TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            source TEXT,
            domain TEXT,
            version INTEGER DEFAULT 1,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vm_search_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection TEXT NOT NULL,
            query_hash TEXT NOT NULL,
            n_results INTEGER NOT NULL,
            elapsed_ms REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def _chroma_client():
    import chromadb
    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(_CHROMA_DIR))


class VectorMemory:
    def __init__(self, collection_name: str = "helios_memory", namespace: str = "default"):
        self._name = collection_name
        self._namespace = namespace
        self._col = None

    def _col_(self):
        if self._col is None:
            client = _chroma_client()
            self._col = client.get_or_create_collection(
                name=self._name,
                metadata={"hnsw:space": "cosine", "namespace": self._namespace},
            )
            meta_conn = _meta_conn()
            meta_conn.execute(
                """INSERT OR IGNORE INTO vm_collection(name, namespace)
                   VALUES(?,?)""",
                (self._name, self._namespace),
            )
            meta_conn.commit()
        return self._col

    def add(
        self,
        text: str,
        embedding: list[float],
        metadata: Optional[dict] = None,
        doc_id: Optional[str] = None,
        source: str = "",
        domain: str = "",
    ) -> str:
        import hashlib
        col = self._col_()
        doc_id = doc_id or str(uuid.uuid4())
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        meta = {
            "source": source, "domain": domain, "namespace": self._namespace,
            "content_hash": content_hash, "version": 1,
            **(metadata or {}),
        }
        col.upsert(ids=[doc_id], embeddings=[embedding], documents=[text], metadatas=[meta])
        db = _meta_conn()
        db.execute(
            """INSERT INTO vm_document(id, collection, namespace, content_hash, source, domain)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
               content_hash=excluded.content_hash, version=version+1,
               updated_at=datetime('now')""",
            (doc_id, self._name, self._namespace, content_hash, source, domain),
        )
        db.execute(
            "UPDATE vm_collection SET doc_count=(SELECT COUNT(*) FROM vm_document WHERE collection=? AND active=1), updated_at=datetime('now') WHERE name=?",
            (self._name, self._name),
        )
        db.commit()
        return doc_id

    def add_batch(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: Optional[list[dict]] = None,
        sources: Optional[list[str]] = None,
        domains: Optional[list[str]] = None,
    ) -> list[str]:
        import hashlib
        col = self._col_()
        ids = [str(uuid.uuid4()) for _ in texts]
        metas = []
        db = _meta_conn()
        for i, (text, emb) in enumerate(zip(texts, embeddings)):
            content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
            src = (sources or [""] * len(texts))[i]
            dom = (domains or [""] * len(texts))[i]
            meta = {
                "source": src, "domain": dom, "namespace": self._namespace,
                "content_hash": content_hash,
                **(metadatas[i] if metadatas else {}),
            }
            metas.append(meta)
            db.execute(
                "INSERT OR IGNORE INTO vm_document(id, collection, namespace, content_hash, source, domain) VALUES(?,?,?,?,?,?)",
                (ids[i], self._name, self._namespace, content_hash, src, dom),
            )
        col.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metas)
        db.execute(
            "UPDATE vm_collection SET doc_count=(SELECT COUNT(*) FROM vm_document WHERE collection=? AND active=1), updated_at=datetime('now') WHERE name=?",
            (self._name, self._name),
        )
        db.commit()
        return ids

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: Optional[dict] = None,
        domain: Optional[str] = None,
    ) -> list[dict]:
        import hashlib
        col = self._col_()
        t0 = time.perf_counter()
        where_filter = {}
        if domain:
            where_filter["domain"] = domain
        if where:
            where_filter.update(where)
        kwargs = {"query_embeddings": [query_embedding], "n_results": min(n_results, max(col.count(), 1))}
        if where_filter:
            kwargs["where"] = where_filter
        res = col.query(**kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        try:
            qhash = hashlib.sha256(str(query_embedding[:5]).encode()).hexdigest()[:8]
            db = _meta_conn()
            db.execute(
                "INSERT INTO vm_search_log(collection, query_hash, n_results, elapsed_ms) VALUES(?,?,?,?)",
                (self._name, qhash, n_results, elapsed),
            )
            db.commit()
        except Exception:
            pass
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0]
        ids = res.get("ids", [[]])[0]
        return [
            {"id": ids[i], "text": docs[i], "metadata": metas[i],
             "score": round(1 - distances[i], 4), "distance": round(distances[i], 4)}
            for i in range(len(docs))
        ]

    def get(self, doc_id: str) -> Optional[dict]:
        col = self._col_()
        res = col.get(ids=[doc_id], include=["documents", "metadatas"])
        if not res["ids"]:
            return None
        return {"id": res["ids"][0], "text": res["documents"][0], "metadata": res["metadatas"][0]}

    def delete(self, doc_id: str):
        col = self._col_()
        col.delete(ids=[doc_id])
        db = _meta_conn()
        db.execute("UPDATE vm_document SET active=0 WHERE id=?", (doc_id,))
        db.commit()

    def prune_by_domain(self, domain: str) -> int:
        col = self._col_()
        res = col.get(where={"domain": domain}, include=[])
        if not res["ids"]:
            return 0
        col.delete(ids=res["ids"])
        db = _meta_conn()
        for doc_id in res["ids"]:
            db.execute("UPDATE vm_document SET active=0 WHERE id=?", (doc_id,))
        db.commit()
        return len(res["ids"])

    def count(self) -> int:
        return self._col_().count()

    def stats(self) -> dict:
        db = _meta_conn()
        row = db.execute(
            "SELECT doc_count, created_at, updated_at FROM vm_collection WHERE name=?",
            (self._name,),
        ).fetchone()
        search_row = db.execute(
            "SELECT COUNT(*) as cnt, AVG(elapsed_ms) as avg_ms FROM vm_search_log WHERE collection=?",
            (self._name,),
        ).fetchone()
        return {
            "collection": self._name, "namespace": self._namespace,
            "doc_count": row["doc_count"] if row else 0,
            "chroma_count": self.count(),
            "searches": search_row["cnt"] or 0,
            "avg_search_ms": round(search_row["avg_ms"] or 0, 2),
            "created_at": row["created_at"] if row else None,
        }


_instances: dict[str, VectorMemory] = {}


def get_memory(collection: str = "helios_memory", namespace: str = "default") -> VectorMemory:
    key = f"{collection}:{namespace}"
    if key not in _instances:
        _instances[key] = VectorMemory(collection, namespace)
    return _instances[key]


def list_collections() -> list[dict]:
    try:
        db = _meta_conn()
        rows = db.execute("SELECT * FROM vm_collection ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
