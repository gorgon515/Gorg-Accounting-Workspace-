"""
Knowledge Engine: ingest, classify, link, version, and quality-score knowledge items.
Embeddings are generated via the real EmbeddingPipeline and stored in ChromaDB.
"""
from __future__ import annotations
import json
import uuid
import hashlib
import sqlite3
from typing import Optional
from .db import get_connection, init_schema

_DOMAINS = [
    "accounting", "tax", "legal", "finance", "markets", "goals",
    "tasks", "clients", "projects", "research", "strategy", "operations", "general",
]

_KINDS = ["document", "decision", "policy", "fact", "procedure", "lesson", "insight", "report"]


def _quality(confidence: float, authority: float, freshness: float, completeness: float) -> float:
    return round((confidence * 0.3 + authority * 0.3 + freshness * 0.2 + completeness * 0.2), 4)


class KnowledgeEngine:
    def __init__(self):
        init_schema()
        self._memory = None
        self._pipeline = None

    def _mem(self):
        if self._memory is None:
            from vector_memory.store import get_memory
            self._memory = get_memory("knowledge", "knowledge")
        return self._memory

    def _pipe(self):
        if self._pipeline is None:
            from embeddings.pipeline import get_pipeline
            self._pipeline = get_pipeline()
        return self._pipeline

    def ingest(
        self,
        title: str,
        content: str,
        domain: str = "general",
        kind: str = "document",
        source: str = "",
        author: str = "",
        confidence: float = 1.0,
        authority: float = 0.5,
        tags: Optional[list] = None,
        citations: Optional[list] = None,
        parent_id: Optional[str] = None,
    ) -> dict:
        item_id = str(uuid.uuid4())
        freshness = 1.0
        completeness = min(1.0, len(content) / 500)
        quality = _quality(confidence, authority, freshness, completeness)
        # embed and store in vector memory
        embed_text = f"{title}\n{content}"
        result = self._pipe().embed(embed_text)
        embed_id = self._mem().add(
            text=embed_text, embedding=result.embedding,
            doc_id=item_id, source=source, domain=domain,
            metadata={"kind": kind, "title": title, "author": author},
        )
        conn = get_connection()
        conn.execute(
            """INSERT INTO knowledge_item
               (id, title, content, domain, kind, source, author,
                confidence, authority, freshness, completeness, quality_score,
                embed_id, tags, citations, parent_id)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (item_id, title, content, domain, kind, source, author,
             confidence, authority, freshness, completeness, quality,
             embed_id, json.dumps(tags or []), json.dumps(citations or []),
             parent_id),
        )
        conn.commit()
        self._detect_conflicts(item_id, content, domain, conn)
        conn.close()
        return self.get(item_id)

    def _detect_conflicts(self, new_id: str, content: str, domain: str, conn: sqlite3.Connection):
        rows = conn.execute(
            "SELECT id, content FROM knowledge_item WHERE domain=? AND status='active' AND id!=?",
            (domain, new_id),
        ).fetchall()
        for row in rows:
            # heuristic: exact same short content in same domain = potential duplicate
            if row["content"].strip() == content.strip() and len(content.strip()) > 20:
                conn.execute(
                    """INSERT OR IGNORE INTO knowledge_conflict
                       (item_a, item_b, conflict_type, description)
                       VALUES(?,?,'duplicate','Same content detected in same domain')""",
                    (new_id, row["id"]),
                )
        conn.commit()

    def get(self, item_id: str) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM knowledge_item WHERE id=?", (item_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return self._fmt(row)

    def _fmt(self, row) -> dict:
        d = dict(row)
        for field in ("tags", "citations"):
            try:
                d[field] = json.loads(d[field])
            except Exception:
                d[field] = []
        return d

    def list(
        self,
        domain: Optional[str] = None,
        kind: Optional[str] = None,
        status: str = "active",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        conn = get_connection()
        clauses = ["status=?"]
        params: list = [status]
        if domain:
            clauses.append("domain=?")
            params.append(domain)
        if kind:
            clauses.append("kind=?")
            params.append(kind)
        rows = conn.execute(
            f"SELECT * FROM knowledge_item WHERE {' AND '.join(clauses)} ORDER BY quality_score DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        conn.close()
        return [self._fmt(r) for r in rows]

    def update(self, item_id: str, **fields) -> Optional[dict]:
        conn = get_connection()
        allowed = {
            "title", "content", "confidence", "authority", "freshness",
            "completeness", "status", "tags", "citations", "source",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            conn.close()
            return self.get(item_id)
        # recompute quality if relevant dims change
        if any(k in updates for k in ("confidence", "authority", "freshness", "completeness")):
            row = conn.execute("SELECT * FROM knowledge_item WHERE id=?", (item_id,)).fetchone()
            if row:
                c = updates.get("confidence", row["confidence"])
                a = updates.get("authority", row["authority"])
                f = updates.get("freshness", row["freshness"])
                comp = updates.get("completeness", row["completeness"])
                updates["quality_score"] = _quality(c, a, f, comp)
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"])
        if "citations" in updates and isinstance(updates["citations"], list):
            updates["citations"] = json.dumps(updates["citations"])
        updates["version"] = "version+1"
        set_parts = []
        vals = []
        for k, v in updates.items():
            if k == "version":
                set_parts.append("version=version+1")
            else:
                set_parts.append(f"{k}=?")
                vals.append(v)
        vals.append(item_id)
        conn.execute(
            f"UPDATE knowledge_item SET {', '.join(set_parts)}, updated_at=datetime('now') WHERE id=?",
            vals,
        )
        conn.commit()
        conn.close()
        # re-embed if content changed
        if "content" in updates or "title" in updates:
            item = self.get(item_id)
            if item:
                embed_text = f"{item['title']}\n{item['content']}"
                result = self._pipe().embed(embed_text)
                self._mem().add(text=embed_text, embedding=result.embedding, doc_id=item_id,
                                source=item["source"], domain=item["domain"])
        return self.get(item_id)

    def link(self, source_id: str, target_id: str, relation: str, weight: float = 1.0):
        conn = get_connection()
        conn.execute(
            """INSERT INTO knowledge_link(source_id, target_id, relation, weight)
               VALUES(?,?,?,?) ON CONFLICT DO NOTHING""",
            (source_id, target_id, relation, weight),
        )
        conn.commit()
        conn.close()

    def links(self, item_id: str) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM knowledge_link WHERE source_id=? OR target_id=?",
            (item_id, item_id),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def conflicts(self, resolved: bool = False) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM knowledge_conflict WHERE resolved=? ORDER BY created_at DESC",
            (1 if resolved else 0,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def resolve_conflict(self, conflict_id: int, resolution: str):
        conn = get_connection()
        conn.execute(
            "UPDATE knowledge_conflict SET resolved=1, resolution=? WHERE id=?",
            (resolution, conflict_id),
        )
        conn.commit()
        conn.close()

    def gaps(self, status: str = "open") -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM knowledge_gap WHERE status=? ORDER BY priority DESC",
            (status,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_gap(self, domain: str, description: str, priority: float = 0.5) -> dict:
        conn = get_connection()
        conn.execute(
            "INSERT INTO knowledge_gap(domain, description, priority) VALUES(?,?,?)",
            (domain, description, priority),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM knowledge_gap ORDER BY rowid DESC LIMIT 1").fetchone()
        conn.close()
        return dict(row)

    def health(self) -> dict:
        conn = get_connection()
        total = conn.execute("SELECT COUNT(*) FROM knowledge_item WHERE status='active'").fetchone()[0]
        avg_q = conn.execute(
            "SELECT AVG(quality_score) FROM knowledge_item WHERE status='active'"
        ).fetchone()[0] or 0
        by_domain = {}
        for row in conn.execute(
            "SELECT domain, COUNT(*) as cnt FROM knowledge_item WHERE status='active' GROUP BY domain"
        ).fetchall():
            by_domain[row[0]] = row[1]
        conflicts_open = conn.execute(
            "SELECT COUNT(*) FROM knowledge_conflict WHERE resolved=0"
        ).fetchone()[0]
        gaps_open = conn.execute("SELECT COUNT(*) FROM knowledge_gap WHERE status='open'").fetchone()[0]
        conn.close()
        return {
            "total_items": total,
            "avg_quality": round(avg_q, 3),
            "by_domain": by_domain,
            "open_conflicts": conflicts_open,
            "open_gaps": gaps_open,
        }

    def stats(self) -> dict:
        h = self.health()
        h["vector_count"] = self._mem().count()
        return h


_instance: Optional["KnowledgeEngine"] = None


def get_knowledge_engine() -> "KnowledgeEngine":
    global _instance
    if _instance is None:
        _instance = KnowledgeEngine()
    return _instance
