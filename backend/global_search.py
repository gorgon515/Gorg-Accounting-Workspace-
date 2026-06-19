"""Global Search — one ranked search across documents, accounting records, tax
research, tasks, clients, and memory. Keyword + token-overlap relevance scoring
(a real, transparent ranker; vector/semantic search is a future upgrade).
"""
from __future__ import annotations

import re
from typing import Optional

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> list[str]:
    return _TOKEN.findall((s or "").lower())


def _score(query_tokens: list[str], text: str) -> int:
    toks = _tokens(text)
    if not toks:
        return 0
    counts = {}
    for t in toks:
        counts[t] = counts.get(t, 0) + 1
    return sum(counts.get(q, 0) for q in query_tokens)


def rank_items(query: str, items: list[dict]) -> list[dict]:
    """items: [{source, title, text, ref}] → scored & sorted (score > 0)."""
    qt = _tokens(query)
    scored = []
    for it in items:
        s = _score(qt, f"{it.get('title','')} {it.get('text','')}")
        if s > 0:
            snippet = (it.get("text") or "")[:160]
            scored.append({"source": it.get("source"), "title": it.get("title"),
                           "ref": it.get("ref"), "score": s, "snippet": snippet})
    scored.sort(key=lambda x: -x["score"])
    return scored


def gather(*, doc_store=None, acct_conn=None, include_tax: bool = True,
           tasks: Optional[list] = None, clients: Optional[list] = None,
           memory: Optional[list] = None) -> list[dict]:
    """Collect searchable items from every available source."""
    items: list[dict] = []
    if doc_store is not None:
        for d in doc_store.search("", limit=300):
            items.append({"source": "document", "title": d.get("filename") or d.get("doc_type"),
                          "text": f"{d.get('doc_type')} {d.get('summary')} {d.get('text')}", "ref": f"doc:{d['id']}"})
    if acct_conn is not None:
        for r in acct_conn.execute("SELECT id, date, memo, source FROM journal_entry ORDER BY id DESC LIMIT 500"):
            items.append({"source": "accounting", "title": f"JE #{r['id']} {r['date']}",
                          "text": f"{r['memo']} {r['source']}", "ref": f"je:{r['id']}"})
        for r in acct_conn.execute("SELECT id, name, kind FROM client"):
            items.append({"source": "client", "title": r["name"], "text": f"{r['name']} {r['kind']}",
                          "ref": f"client:{r['id']}"})
    if include_tax:
        from tax_research import engine as tax
        for k, v in tax.TAX_TOPICS.items():
            items.append({"source": "tax_research", "title": v["issue"],
                          "text": f"{v['summary']} {' '.join(v['keywords'])}", "ref": f"tax:{k}"})
    for t in tasks or []:
        items.append({"source": "task", "title": t.get("title"), "text": t.get("title", ""),
                      "ref": f"task:{t.get('id')}"})
    for c in clients or []:
        items.append({"source": "client", "title": c.get("name"), "text": c.get("name", ""),
                      "ref": f"client:{c.get('id')}"})
    for m in memory or []:
        items.append({"source": "memory", "title": m.get("fact", "")[:40], "text": m.get("fact", ""),
                      "ref": f"mem:{m.get('id')}"})
    return items


def search_all(query: str, **sources) -> dict:
    items = gather(**sources)
    results = rank_items(query, items)
    by_source: dict[str, int] = {}
    for r in results:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
    return {"query": query, "count": len(results), "by_source": by_source, "results": results[:50]}
