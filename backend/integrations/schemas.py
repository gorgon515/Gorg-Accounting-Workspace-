"""Normalized Email / Event shapes + adapters from Gmail and Microsoft Graph.

The intelligence engines (email_intel, calendar_intel) consume these normalized
shapes, so they work identically against Google and Outlook. The ``normalize_*``
functions are pure and unit-tested against real-format API fixtures.
"""
from __future__ import annotations

import base64
from typing import Optional


def _b64url(data: Optional[str]) -> str:
    if not data:
        return ""
    pad = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + pad).decode("utf-8", "replace")
    except Exception:
        return ""


# ---- Email ----
def normalize_gmail(msg: dict) -> dict:
    payload = msg.get("payload", {}) or {}
    headers = {h.get("name", "").lower(): h.get("value", "") for h in payload.get("headers", [])}
    body = ""
    if payload.get("body", {}).get("data"):
        body = _b64url(payload["body"]["data"])
    else:
        for part in payload.get("parts", []) or []:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body = _b64url(part["body"]["data"])
                break
    labels = msg.get("labelIds", []) or []
    return {
        "id": msg.get("id"),
        "source": "gmail",
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "snippet": msg.get("snippet", ""),
        "body": body,
        "date": headers.get("date", ""),
        "labels": labels,
        "unread": "UNREAD" in labels,
    }


def normalize_graph_message(msg: dict) -> dict:
    frm = (msg.get("from", {}) or {}).get("emailAddress", {}) or {}
    to = [r.get("emailAddress", {}).get("address", "") for r in msg.get("toRecipients", []) or []]
    return {
        "id": msg.get("id"),
        "source": "outlook",
        "from": frm.get("address", ""),
        "to": ", ".join(to),
        "subject": msg.get("subject", ""),
        "snippet": msg.get("bodyPreview", ""),
        "body": (msg.get("body", {}) or {}).get("content", ""),
        "date": msg.get("receivedDateTime", ""),
        "labels": [],
        "unread": not msg.get("isRead", True),
    }


# ---- Event ----
def normalize_gcal_event(e: dict) -> dict:
    start = (e.get("start", {}) or {})
    end = (e.get("end", {}) or {})
    return {
        "id": e.get("id"),
        "source": "gcal",
        "title": e.get("summary", "(no title)"),
        "start": start.get("dateTime") or start.get("date") or "",
        "end": end.get("dateTime") or end.get("date") or "",
        "location": e.get("location", ""),
        "attendees": [a.get("email", "") for a in e.get("attendees", []) or []],
        "all_day": "date" in start and "dateTime" not in start,
    }


def normalize_graph_event(e: dict) -> dict:
    start = (e.get("start", {}) or {})
    end = (e.get("end", {}) or {})
    return {
        "id": e.get("id"),
        "source": "outlook",
        "title": e.get("subject", "(no title)"),
        "start": start.get("dateTime", ""),
        "end": end.get("dateTime", ""),
        "location": (e.get("location", {}) or {}).get("displayName", ""),
        "attendees": [a.get("emailAddress", {}).get("address", "") for a in e.get("attendees", []) or []],
        "all_day": bool(e.get("isAllDay", False)),
    }
