"""RSS 2.0 and Atom feed parsing using the standard-library XML parser.

Returns a uniform list of entry dicts: {title, link, summary, published, guid}.
Namespace-tolerant so it handles both feed dialects the standard-setters publish.
No third-party dependencies — this is the unit-tested core the collectors rely on.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Optional

_ATOM = "{http://www.w3.org/2005/Atom}"


def _localtag(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _text(el: Optional[ET.Element]) -> str:
    if el is None:
        return ""
    return (el.text or "").strip()


def _strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def parse(xml_text: str) -> list[dict]:
    """Parse an RSS or Atom document into a list of normalized entry dicts."""
    if not xml_text or not xml_text.strip():
        return []
    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError:
        return []

    tag = _localtag(root.tag).lower()
    if tag == "feed":
        return _parse_atom(root)
    # rss → channel → item ; some feeds are rdf:RDF with item children.
    return _parse_rss(root)


def _parse_rss(root: ET.Element) -> list[dict]:
    items: list[dict] = []
    # Items may be under <channel> (RSS 2.0) or directly (RDF).
    candidates = root.findall(".//{*}item") or root.findall(".//item")
    for it in candidates:
        get = lambda name: it.find(f"{{*}}{name}")  # noqa: E731
        link = _text(get("link"))
        guid = _text(get("guid")) or link
        summary = _strip_html(_text(get("description")) or _text(get("summary")))
        items.append({
            "title": _strip_html(_text(get("title"))),
            "link": link,
            "summary": summary,
            "published": _text(get("pubDate")) or _text(get("date")) or None,
            "guid": guid or None,
        })
    return items


def _parse_atom(root: ET.Element) -> list[dict]:
    items: list[dict] = []
    for e in root.findall(f"{_ATOM}entry") or root.findall(".//{*}entry"):
        # Atom <link href="..."> (prefer rel=alternate / first http link).
        link = ""
        for l in e.findall(f"{_ATOM}link") or e.findall("{*}link"):
            href = l.get("href", "")
            rel = l.get("rel", "alternate")
            if href and (rel == "alternate" or not link):
                link = href
                if rel == "alternate":
                    break
        summary = _strip_html(_text(e.find(f"{_ATOM}summary")) or _text(e.find(f"{_ATOM}content"))
                              or _text(e.find("{*}summary")) or _text(e.find("{*}content")))
        items.append({
            "title": _strip_html(_text(e.find(f"{_ATOM}title")) or _text(e.find("{*}title"))),
            "link": link,
            "summary": summary,
            "published": (_text(e.find(f"{_ATOM}updated")) or _text(e.find(f"{_ATOM}published"))
                          or _text(e.find("{*}updated")) or None),
            "guid": _text(e.find(f"{_ATOM}id")) or _text(e.find("{*}id")) or link or None,
        })
    return items
