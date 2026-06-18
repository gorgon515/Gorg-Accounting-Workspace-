"""
RAG Retriever: hybrid retrieval combining semantic vector search + BM25 keyword search.
Reranks by combined score. Tracks citations and source confidence.
"""
import math
import sqlite3
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

_LOG_DB = Path(".data/rag.db")


def _log_conn() -> sqlite3.Connection:
    _LOG_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_LOG_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS retrieval_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            collection TEXT NOT NULL,
            n_semantic INTEGER NOT NULL,
            n_keyword INTEGER NOT NULL,
            n_final INTEGER NOT NULL,
            semantic_weight REAL NOT NULL,
            keyword_weight REAL NOT NULL,
            elapsed_ms REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS citation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            doc_title TEXT,
            source TEXT,
            score REAL NOT NULL,
            rank INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


@dataclass
class RetrievedDoc:
    id: str
    text: str
    score: float
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    source: str = ""
    domain: str = ""
    metadata: dict = field(default_factory=dict)
    rank: int = 0


class HybridRetriever:
    def __init__(
        self,
        collection: str = "knowledge",
        semantic_weight: float = 0.65,
        keyword_weight: float = 0.35,
    ):
        self._collection = collection
        self._sw = semantic_weight
        self._kw = keyword_weight
        self._memory = None
        self._pipeline = None

    def _mem(self):
        if self._memory is None:
            from vector_memory.store import get_memory
            self._memory = get_memory(self._collection, "knowledge")
        return self._memory

    def _pipe(self):
        if self._pipeline is None:
            from embeddings.pipeline import get_pipeline
            self._pipeline = get_pipeline()
        return self._pipeline

    def retrieve(
        self,
        query: str,
        n_results: int = 10,
        domain: Optional[str] = None,
        semantic_only: bool = False,
    ) -> list[RetrievedDoc]:
        import time
        t0 = time.perf_counter()

        # semantic search
        q_emb = self._pipe().embed(query).embedding
        sem_results = self._mem().search(q_emb, n_results=n_results * 2, domain=domain)
        sem_map = {r["id"]: r for r in sem_results}

        # keyword (BM25) search over retrieved semantic docs
        keyword_scores: dict[str, float] = {}
        if not semantic_only and sem_results:
            corpus = [r["text"] for r in sem_results]
            ids = [r["id"] for r in sem_results]
            try:
                from rank_bm25 import BM25Okapi
                tokenized = [doc.lower().split() for doc in corpus]
                bm25 = BM25Okapi(tokenized)
                q_tokens = query.lower().split()
                scores = bm25.get_scores(q_tokens)
                max_bm25 = max(scores) if max(scores) > 0 else 1
                for idx, doc_id in enumerate(ids):
                    keyword_scores[doc_id] = scores[idx] / max_bm25
            except Exception:
                pass

        # combine scores
        combined: dict[str, float] = {}
        for r in sem_results:
            did = r["id"]
            s_score = r["score"]
            k_score = keyword_scores.get(did, 0.0)
            combined[did] = self._sw * s_score + self._kw * k_score

        ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:n_results]

        docs = []
        for rank, (did, score) in enumerate(ranked):
            raw = sem_map[did]
            meta = raw.get("metadata", {})
            docs.append(RetrievedDoc(
                id=did, text=raw["text"], score=round(score, 4),
                semantic_score=round(raw["score"], 4),
                keyword_score=round(keyword_scores.get(did, 0.0), 4),
                source=meta.get("source", ""), domain=meta.get("domain", ""),
                metadata=meta, rank=rank + 1,
            ))

        elapsed = (time.perf_counter() - t0) * 1000
        try:
            db = _log_conn()
            db.execute(
                """INSERT INTO retrieval_log
                   (query_text, collection, n_semantic, n_keyword, n_final,
                    semantic_weight, keyword_weight, elapsed_ms)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (query[:500], self._collection, len(sem_results),
                 len(keyword_scores), len(docs), self._sw, self._kw, elapsed),
            )
            for doc in docs:
                db.execute(
                    """INSERT INTO citation_log
                       (query_text, doc_id, doc_title, source, score, rank)
                       VALUES(?,?,?,?,?,?)""",
                    (query[:500], doc.id,
                     doc.metadata.get("title", ""), doc.source, doc.score, doc.rank),
                )
            db.commit()
        except Exception:
            pass

        return docs

    def stats(self) -> dict:
        try:
            db = _log_conn()
            row = db.execute(
                "SELECT COUNT(*) as cnt, AVG(elapsed_ms) as avg_ms FROM retrieval_log WHERE collection=?",
                (self._collection,),
            ).fetchone()
            return {
                "collection": self._collection,
                "total_retrievals": row["cnt"] or 0,
                "avg_elapsed_ms": round(row["avg_ms"] or 0, 2),
                "semantic_weight": self._sw,
                "keyword_weight": self._kw,
            }
        except Exception:
            return {"collection": self._collection}


_instances: dict[str, HybridRetriever] = {}


def get_retriever(collection: str = "knowledge") -> HybridRetriever:
    if collection not in _instances:
        _instances[collection] = HybridRetriever(collection)
    return _instances[collection]
