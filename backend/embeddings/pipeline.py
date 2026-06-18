"""
Real local embedding inference.

Two backends:
  - "local": TF-IDF + TruncatedSVD (Latent Semantic Analysis). Works fully
    offline with no downloads. Produces real content-derived dense vectors.
  - "minilm", "bge-small", etc.: sentence-transformers. Requires a cached or
    downloadable HuggingFace model.

The "local" backend is the default for environments without internet access.
"""
from __future__ import annotations
import os
import time
import hashlib
import pickle
import sqlite3
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

_MODEL_DIR = Path(".data/models")
_META_DB = Path(".data/embeddings.db")
_LSA_PATH = Path(".data/models/lsa_model.pkl")

_TRANSFORMER_MODELS = {
    "bge-small": "BAAI/bge-small-en-v1.5",
    "minilm": "all-MiniLM-L6-v2",
    "minilm-l12": "all-MiniLM-L12-v2",
    "e5-small": "intfloat/e5-small-v2",
}
_DEFAULT_MODEL = "local"

# Dimension for LSA embeddings
_LSA_DIM = 128

# Seed corpus so the LSA model works even with no ingested data yet
_SEED_CORPUS = [
    "revenue income profit loss cash flow financial statement",
    "tax deduction credit return filing quarterly annual",
    "invoice accounts receivable payable billing collection",
    "budget forecast planning scenario analysis projection",
    "risk assessment mitigation probability impact severity",
    "opportunity growth strategy expansion market competitive",
    "expense cost reduction efficiency operations workflow",
    "client customer project engagement service delivery",
    "asset liability equity balance sheet capital",
    "goals milestones objectives targets performance KPI",
    "compliance regulation audit policy procedure internal control",
    "market volatility portfolio investment allocation returns",
    "payroll employee headcount salary benefits workforce",
    "knowledge document research synthesis retrieval semantic",
    "decision approval rejection proposal recommendation action",
]


@dataclass
class EmbedResult:
    text: str
    embedding: list[float]
    model: str
    dim: int
    elapsed_ms: float


def _get_meta_conn() -> sqlite3.Connection:
    _META_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_META_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS embed_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            dim INTEGER NOT NULL,
            elapsed_ms REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_benchmark (
            model TEXT PRIMARY KEY,
            avg_ms REAL,
            dim INTEGER,
            sample_count INTEGER DEFAULT 0,
            last_run TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


class LSAEmbedder:
    """
    TF-IDF + TruncatedSVD (LSA) embedder.
    Works fully offline. The vectorizer is fitted incrementally as new texts
    are added; the model is persisted to disk so it improves over time.
    """
    def __init__(self, dim: int = _LSA_DIM):
        self._dim = dim
        self._tfidf = None
        self._svd = None
        self._fitted = False
        self._corpus: list[str] = list(_SEED_CORPUS)
        self._load_or_init()

    def _load_or_init(self):
        if _LSA_PATH.exists():
            try:
                with open(_LSA_PATH, "rb") as f:
                    state = pickle.load(f)
                self._tfidf = state["tfidf"]
                self._svd = state["svd"]
                self._corpus = state.get("corpus", self._corpus)
                # lock dimension from saved model — never change after first fit
                self._dim = self._svd.n_components
                self._fitted = True
                return
            except Exception:
                pass
        self._fit(self._corpus)

    def _fit(self, corpus: list[str], lock_dim: bool = False):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        import numpy as np
        self._tfidf = TfidfVectorizer(
            max_features=8000, ngram_range=(1, 2), sublinear_tf=True, min_df=1,
        )
        tfidf_matrix = self._tfidf.fit_transform(corpus)
        # If we already have a fixed dimension, keep it; otherwise compute max possible
        if lock_dim and self._dim:
            n_components = self._dim
        else:
            n_components = min(self._dim, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
        n_components = max(n_components, 2)
        # Clamp to actual matrix size
        n_components = min(n_components, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
        self._svd = TruncatedSVD(n_components=n_components, random_state=42)
        self._svd.fit(tfidf_matrix)
        self._fitted = True
        self._dim = n_components  # locked after first fit
        self._save()

    def _save(self):
        try:
            _LSA_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_LSA_PATH, "wb") as f:
                pickle.dump({"tfidf": self._tfidf, "svd": self._svd, "corpus": self._corpus}, f)
        except Exception:
            pass

    def embed(self, text: str) -> list[float]:
        import numpy as np
        # re-fit if corpus grew significantly, but lock dimension
        if text not in self._corpus:
            self._corpus.append(text)
            if len(self._corpus) % 20 == 0:
                self._fit(self._corpus, lock_dim=True)
        vec = self._tfidf.transform([text])
        reduced = self._svd.transform(vec)[0]
        norm = np.linalg.norm(reduced)
        if norm > 0:
            reduced = reduced / norm
        return reduced.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import numpy as np
        new_texts = [t for t in texts if t not in self._corpus]
        if new_texts:
            self._corpus.extend(new_texts)
            self._fit(self._corpus, lock_dim=True)
        mat = self._tfidf.transform(texts)
        reduced = self._svd.transform(mat)
        norms = np.linalg.norm(reduced, axis=1, keepdims=True)
        norms[norms == 0] = 1
        reduced = reduced / norms
        return reduced.tolist()

    @property
    def dim(self) -> int:
        return self._dim


_lsa_instance: Optional[LSAEmbedder] = None


def _get_lsa() -> LSAEmbedder:
    global _lsa_instance
    if _lsa_instance is None:
        _lsa_instance = LSAEmbedder()
    return _lsa_instance


class EmbeddingPipeline:
    def __init__(self, model_name: str = _DEFAULT_MODEL):
        self._model_name = model_name
        self._model_id = _TRANSFORMER_MODELS.get(model_name, model_name)
        self._transformer = None
        self._dim: Optional[int] = None
        self._use_lsa = model_name == "local"

    def _load_transformer(self):
        if self._transformer is not None:
            return
        from sentence_transformers import SentenceTransformer
        _MODEL_DIR.mkdir(parents=True, exist_ok=True)
        self._transformer = SentenceTransformer(self._model_id, cache_folder=str(_MODEL_DIR))
        probe = self._transformer.encode(["warmup"], normalize_embeddings=True)
        self._dim = probe.shape[1]

    def _embed_one(self, text: str) -> tuple[list[float], int]:
        if self._use_lsa:
            lsa = _get_lsa()
            vec = lsa.embed(text)
            return vec, lsa.dim
        else:
            self._load_transformer()
            import numpy as np
            vec = self._transformer.encode([text], normalize_embeddings=True)[0]
            return vec.tolist(), self._dim

    def embed(self, text: str) -> EmbedResult:
        t0 = time.perf_counter()
        vec, dim = self._embed_one(text)
        elapsed = (time.perf_counter() - t0) * 1000
        result = EmbedResult(
            text=text, embedding=vec, model=self._model_name,
            dim=dim, elapsed_ms=round(elapsed, 2),
        )
        try:
            conn = _get_meta_conn()
            h = hashlib.sha256(text.encode()).hexdigest()[:16]
            conn.execute(
                "INSERT INTO embed_log(model, text_hash, dim, elapsed_ms) VALUES(?,?,?,?)",
                (self._model_name, h, dim, elapsed),
            )
            conn.commit()
        except Exception:
            pass
        return result

    def embed_batch(self, texts: list[str], batch_size: int = 64) -> list[EmbedResult]:
        results = []
        if self._use_lsa:
            lsa = _get_lsa()
            t0 = time.perf_counter()
            vecs = lsa.embed_batch(texts)
            elapsed = (time.perf_counter() - t0) * 1000
            per_ms = elapsed / max(len(texts), 1)
            for text, vec in zip(texts, vecs):
                results.append(EmbedResult(text=text, embedding=vec, model=self._model_name,
                                           dim=lsa.dim, elapsed_ms=round(per_ms, 2)))
        else:
            self._load_transformer()
            for i in range(0, len(texts), batch_size):
                chunk = texts[i: i + batch_size]
                t0 = time.perf_counter()
                vecs = self._transformer.encode(chunk, normalize_embeddings=True, batch_size=batch_size)
                elapsed = (time.perf_counter() - t0) * 1000
                per_ms = elapsed / max(len(chunk), 1)
                for text, vec in zip(chunk, vecs):
                    results.append(EmbedResult(text=text, embedding=vec.tolist(),
                                               model=self._model_name, dim=self._dim,
                                               elapsed_ms=round(per_ms, 2)))
        return results

    def dimension(self) -> int:
        if self._use_lsa:
            return _get_lsa().dim
        self._load_transformer()
        return self._dim

    def model_id(self) -> str:
        if self._use_lsa:
            return "local/lsa-tfidf-svd"
        return self._model_id

    def benchmark(self, n: int = 20) -> dict:
        samples = [f"Benchmark sentence number {i} for testing embedding performance." for i in range(n)]
        t0 = time.perf_counter()
        self.embed_batch(samples)
        elapsed = (time.perf_counter() - t0) * 1000
        avg_ms = elapsed / n
        dim = self.dimension()
        try:
            conn = _get_meta_conn()
            conn.execute(
                """INSERT INTO model_benchmark(model, avg_ms, dim, sample_count)
                   VALUES(?,?,?,?)
                   ON CONFLICT(model) DO UPDATE SET
                   avg_ms=excluded.avg_ms, dim=excluded.dim,
                   sample_count=excluded.sample_count, last_run=datetime('now')""",
                (self._model_name, avg_ms, dim, n),
            )
            conn.commit()
        except Exception:
            pass
        return {"model": self._model_name, "model_id": self.model_id(),
                "dim": dim, "samples": n,
                "total_ms": round(elapsed, 2), "avg_ms_per_doc": round(avg_ms, 2)}

    def quality_score(self, sentence_a: str, sentence_b: str) -> float:
        import numpy as np
        va, _ = self._embed_one(sentence_a)
        vb, _ = self._embed_one(sentence_b)
        return float(np.dot(va, vb))

    def stats(self) -> dict:
        dim = self.dimension()
        try:
            conn = _get_meta_conn()
            row = conn.execute(
                "SELECT COUNT(*) as cnt, AVG(elapsed_ms) as avg_ms FROM embed_log WHERE model=?",
                (self._model_name,),
            ).fetchone()
            bench = conn.execute(
                "SELECT * FROM model_benchmark WHERE model=?", (self._model_name,)
            ).fetchone()
            return {
                "model": self._model_name, "model_id": self.model_id(),
                "dim": dim, "total_embedded": row["cnt"],
                "avg_ms": round(row["avg_ms"] or 0, 2),
                "benchmark": dict(bench) if bench else None,
            }
        except Exception:
            return {"model": self._model_name, "dim": dim}


_instances: dict[str, EmbeddingPipeline] = {}


def get_pipeline(model: str = _DEFAULT_MODEL) -> EmbeddingPipeline:
    if model not in _instances:
        _instances[model] = EmbeddingPipeline(model)
    return _instances[model]


def list_models() -> list[dict]:
    result = [{"key": "local", "model_id": "local/lsa-tfidf-svd",
               "description": "TF-IDF + TruncatedSVD (LSA) — offline, no download"}]
    result += [{"key": k, "model_id": v, "description": "sentence-transformers (requires model cache)"}
               for k, v in _TRANSFORMER_MODELS.items()]
    return result
