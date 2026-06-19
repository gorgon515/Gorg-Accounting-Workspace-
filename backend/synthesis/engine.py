"""
Research Synthesis Engine: multi-source synthesis, conflict/consensus detection,
citation generation, knowledge gap identification, summarization.
"""
import json
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

_DB = Path(".data/synthesis.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS synthesis_report (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            summary TEXT NOT NULL,
            consensus TEXT DEFAULT '[]',
            conflicts TEXT DEFAULT '[]',
            gaps TEXT DEFAULT '[]',
            citations TEXT DEFAULT '[]',
            confidence REAL DEFAULT 0.5,
            source_count INTEGER DEFAULT 0,
            domain TEXT DEFAULT 'general',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def _extract_key_sentences(text: str, n: int = 3) -> list[str]:
    """Extract top N sentences by length as a naive extractive summarizer."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    # rank by: not a header, has nouns (capitalized words as proxy), longer = more info
    scored = [(len(s) * (1 + s.count(',') * 0.1), s) for s in sentences]
    scored.sort(reverse=True)
    return [s for _, s in scored[:n]]


def _detect_conflicts(docs: list[dict]) -> list[str]:
    conflicts = []
    # simple heuristic: contradictory numeric claims or opposing keywords
    negation_pairs = [
        (r'\bincrease\b', r'\bdecrease\b'),
        (r'\bgrowth\b', r'\bdecline\b'),
        (r'\bprofit\b', r'\bloss\b'),
        (r'\bapproved\b', r'\brejected\b'),
    ]
    texts = [d.get("text", "") for d in docs]
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            for pos, neg in negation_pairs:
                if re.search(pos, texts[i], re.I) and re.search(neg, texts[j], re.I):
                    conflicts.append(
                        f"Source {i+1} suggests '{pos.strip(chr(92)+'b')}' while source {j+1} suggests '{neg.strip(chr(92)+'b')}'"
                    )
    return conflicts[:5]


def _detect_consensus(docs: list[dict]) -> list[str]:
    if len(docs) < 2:
        return []
    from collections import Counter
    # find phrases (2-grams) that appear in multiple documents
    phrase_docs: dict[str, int] = {}
    for d in docs:
        words = d.get("text", "").lower().split()
        bigrams = {f"{words[i]} {words[i+1]}" for i in range(len(words)-1)
                   if len(words[i]) > 3 and len(words[i+1]) > 3}
        for bg in bigrams:
            phrase_docs[bg] = phrase_docs.get(bg, 0) + 1
    consensus_phrases = [p for p, cnt in phrase_docs.items() if cnt >= max(2, len(docs) // 2)]
    return [f"Multiple sources agree on: '{p}'" for p in sorted(consensus_phrases, key=lambda x: -phrase_docs[x])[:3]]


class SynthesisEngine:
    def synthesize(
        self,
        query: str,
        n_sources: int = 8,
        domain: Optional[str] = None,
    ) -> dict:
        from rag.platform import get_rag
        rag = get_rag()
        rag_result = rag.query(query, n_results=n_sources, domain=domain)
        docs = rag_result.get("citations", [])

        # build a text corpus from retrieved docs via context
        context = rag_result.get("context", "")
        doc_texts = []
        for part in context.split("\n\n"):
            part = part.strip()
            if part.startswith("["):
                doc_texts.append({"text": part})

        # extractive summary
        all_text = " ".join(d.get("text", "") for d in doc_texts)
        key_sentences = _extract_key_sentences(all_text, n=5)
        summary = " ".join(key_sentences) if key_sentences else "Insufficient knowledge to synthesize."

        conflicts = _detect_conflicts(doc_texts)
        consensus = _detect_consensus(doc_texts)

        # knowledge gaps: things the query mentions that have no coverage
        query_terms = set(query.lower().split()) - {"the", "a", "an", "in", "of", "for", "and", "or"}
        covered_terms = set(all_text.lower().split())
        gaps = [f"No information found about: '{t}'" for t in list(query_terms - covered_terms)[:3]]

        report_id = str(uuid.uuid4())
        report = {
            "id": report_id,
            "query": query,
            "summary": summary,
            "consensus": consensus,
            "conflicts": conflicts,
            "gaps": gaps,
            "citations": docs,
            "confidence": rag_result.get("confidence", 0.5),
            "hallucination_risk": rag_result.get("hallucination_risk", 1.0),
            "source_count": rag_result.get("n_docs", 0),
            "domain": domain or "general",
        }

        try:
            db = _conn()
            db.execute(
                """INSERT INTO synthesis_report
                   (id, query, summary, consensus, conflicts, gaps, citations, confidence, source_count, domain)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (report_id, query, summary,
                 json.dumps(consensus), json.dumps(conflicts), json.dumps(gaps),
                 json.dumps(docs), report["confidence"], report["source_count"], report["domain"]),
            )
            db.commit()
        except Exception:
            pass

        return report

    def get_report(self, report_id: str) -> Optional[dict]:
        try:
            db = _conn()
            row = db.execute(
                "SELECT * FROM synthesis_report WHERE id=?", (report_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            for f in ("consensus", "conflicts", "gaps", "citations"):
                try:
                    d[f] = json.loads(d[f])
                except Exception:
                    d[f] = []
            return d
        except Exception:
            return None

    def list_reports(self, domain: Optional[str] = None, limit: int = 20) -> list[dict]:
        try:
            db = _conn()
            if domain:
                rows = db.execute(
                    "SELECT * FROM synthesis_report WHERE domain=? ORDER BY created_at DESC LIMIT ?",
                    (domain, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM synthesis_report ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                for f in ("consensus", "conflicts", "gaps", "citations"):
                    try:
                        d[f] = json.loads(d[f])
                    except Exception:
                        d[f] = []
                results.append(d)
            return results
        except Exception:
            return []

    def stats(self) -> dict:
        try:
            db = _conn()
            row = db.execute(
                "SELECT COUNT(*) as cnt, AVG(confidence) as avg_conf FROM synthesis_report"
            ).fetchone()
            return {
                "total_reports": row["cnt"] or 0,
                "avg_confidence": round(row["avg_conf"] or 0, 3),
            }
        except Exception:
            return {"total_reports": 0}


_instance: Optional["SynthesisEngine"] = None


def get_synthesis_engine() -> "SynthesisEngine":
    global _instance
    if _instance is None:
        _instance = SynthesisEngine()
    return _instance
