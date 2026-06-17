"""Document Center — metadata store with tagging, versioning, and linking.

Stores document metadata + a path (OCR-ready: a text/ocr field can be added and
indexed later). Versioning supersedes prior records; search spans title/type/tags.
"""
from __future__ import annotations

import json
from typing import Optional

from .db import audit, now_iso


def add_document(conn, title: str, *, doc_type: str = "", path: str = "", tags: Optional[list] = None,
                 client_id: Optional[int] = None, link_entity: Optional[str] = None,
                 link_id: Optional[int] = None, user: str = "system") -> dict:
    cur = conn.execute(
        "INSERT INTO document (title,doc_type,path,tags,client_id,link_entity,link_id,version,created_at) "
        "VALUES (?,?,?,?,?,?,?,1,?)",
        (title, doc_type, path, json.dumps(tags or []), client_id, link_entity, link_id, now_iso()))
    conn.commit()
    audit(conn, entity="document", entity_id=cur.lastrowid, action="create",
          new={"title": title, "type": doc_type}, user=user)
    conn.commit()
    return get_document(conn, cur.lastrowid)


def get_document(conn, doc_id: int) -> Optional[dict]:
    r = conn.execute("SELECT * FROM document WHERE id=?", (doc_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["tags"] = json.loads(d["tags"] or "[]")
    return d


def new_version(conn, doc_id: int, *, path: str = "", title: Optional[str] = None, user: str = "system") -> dict:
    prev = get_document(conn, doc_id)
    if not prev:
        raise ValueError("unknown document")
    cur = conn.execute(
        "INSERT INTO document (title,doc_type,path,tags,client_id,link_entity,link_id,version,supersedes,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (title or prev["title"], prev["doc_type"], path or prev["path"], json.dumps(prev["tags"]),
         prev["client_id"], prev["link_entity"], prev["link_id"], prev["version"] + 1, doc_id, now_iso()))
    conn.commit()
    audit(conn, entity="document", entity_id=cur.lastrowid, action="new_version",
          old={"id": doc_id, "version": prev["version"]}, new={"version": prev["version"] + 1}, user=user)
    conn.commit()
    return get_document(conn, cur.lastrowid)


def search(conn, query: str = "", *, doc_type: Optional[str] = None, tag: Optional[str] = None,
           client_id: Optional[int] = None) -> list[dict]:
    rows = [dict(r) for r in conn.execute("SELECT * FROM document ORDER BY created_at DESC")]
    out = []
    q = query.lower()
    for r in rows:
        r["tags"] = json.loads(r["tags"] or "[]")
        if q and q not in (r["title"] or "").lower() and q not in (r["doc_type"] or "").lower():
            continue
        if doc_type and r["doc_type"] != doc_type:
            continue
        if tag and tag not in r["tags"]:
            continue
        if client_id and r["client_id"] != client_id:
            continue
        out.append(r)
    return out
