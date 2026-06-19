"""
RAG Platform: query assembly, context building, citation tracking, confidence scoring,
hallucination risk detection.
"""
import re
import time
import sqlite3
from pathlib import Path
from typing import Optional
from .retriever import get_retriever, RetrievedDoc

_LOG_DB = Path(".data/rag.db")


def _conn() -> sqlite3.Connection:
    from .retriever import _log_conn
    return _log_conn()


def _hallucination_risk(query: str, docs: list[RetrievedDoc]) -> float:
    """
    Simple heuristic: if top docs have low scores, or coverage of query
    terms is poor, risk is higher.
    """
    if not docs:
        return 1.0
    avg_score = sum(d.score for d in docs) / len(docs)
    top_score = docs[0].score if docs else 0
    query_terms = set(query.lower().split())
    covered = set()
    for d in docs[:3]:
        doc_terms = set(d.text.lower().split())
        covered |= query_terms & doc_terms
    term_coverage = len(covered) / max(len(query_terms), 1)
    # lower score → higher risk; less coverage → higher risk
    risk = (1 - avg_score) * 0.4 + (1 - top_score) * 0.3 + (1 - term_coverage) * 0.3
    return round(min(max(risk, 0.0), 1.0), 3)


def _confidence(docs: list[RetrievedDoc]) -> float:
    if not docs:
        return 0.0
    weighted = sum((1.0 / (d.rank + 1)) * d.score for d in docs)
    norm = sum(1.0 / (d.rank + 1) for d in docs)
    return round(weighted / max(norm, 1e-9), 4)


class RAGPlatform:
    def __init__(self, collection: str = "knowledge"):
        self._collection = collection
        self._retriever = get_retriever(collection)

    def query(
        self,
        question: str,
        n_results: int = 8,
        domain: Optional[str] = None,
        semantic_only: bool = False,
        include_memory: bool = True,
    ) -> dict:
        docs = self._retriever.retrieve(question, n_results=n_results,
                                        domain=domain, semantic_only=semantic_only)

        # optionally also pull from institutional memory
        memory_docs = []
        if include_memory:
            from knowledge.memory import get_institutional_memory
            mem = get_institutional_memory()
            kw_results = mem.search_by_keyword(question, limit=3)
            for r in kw_results:
                memory_docs.append({
                    "id": r["id"], "text": f"{r['title']}: {r['description']}",
                    "source": "institutional_memory", "domain": r["domain"],
                    "score": 0.5,
                })

        context_parts = []
        citations = []
        for i, doc in enumerate(docs):
            context_parts.append(f"[{i+1}] {doc.text[:800]}")
            citations.append({
                "ref": i + 1, "id": doc.id, "source": doc.source,
                "domain": doc.domain, "score": doc.score,
                "title": doc.metadata.get("title", ""),
            })

        for i, mem_doc in enumerate(memory_docs, start=len(docs) + 1):
            context_parts.append(f"[{i}] (Memory) {mem_doc['text'][:400]}")
            citations.append({"ref": i, "id": mem_doc["id"], "source": mem_doc["source"],
                              "domain": mem_doc["domain"], "score": mem_doc["score"], "title": ""})

        context = "\n\n".join(context_parts)
        confidence = _confidence(docs)
        hallucination_risk = _hallucination_risk(question, docs)

        return {
            "question": question,
            "context": context,
            "citations": citations,
            "n_docs": len(docs),
            "n_memory": len(memory_docs),
            "confidence": confidence,
            "hallucination_risk": hallucination_risk,
            "domain": domain,
        }

    def search(
        self,
        query: str,
        n_results: int = 10,
        domain: Optional[str] = None,
    ) -> list[dict]:
        docs = self._retriever.retrieve(query, n_results=n_results, domain=domain)
        return [
            {
                "id": d.id, "text": d.text, "score": d.score,
                "semantic_score": d.semantic_score, "keyword_score": d.keyword_score,
                "source": d.source, "domain": d.domain, "rank": d.rank,
                "metadata": d.metadata,
            }
            for d in docs
        ]

    def retrieval_metrics(self) -> dict:
        return self._retriever.stats()


_instances: dict[str, "RAGPlatform"] = {}


def get_rag(collection: str = "knowledge") -> "RAGPlatform":
    if collection not in _instances:
        _instances[collection] = RAGPlatform(collection)
    return _instances[collection]
