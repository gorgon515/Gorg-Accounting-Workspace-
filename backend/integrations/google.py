"""Google Workspace integration — OAuth 2.0 + Gmail / Calendar / Tasks.

Real REST calls to Google APIs, network-guarded. OAuth URL building and token
exchange/refresh request construction are pure and unit-tested; the live calls
work with a configured OAuth client (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET) and
a stored refresh token. Responses are normalized via integrations.schemas.
"""
from __future__ import annotations

import os
import urllib.parse
from typing import Optional

from .schemas import normalize_gcal_event, normalize_gmail

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]


class GoogleAuthError(RuntimeError):
    pass


def auth_url(client_id: str, redirect_uri: str, scopes: Optional[list[str]] = None, state: str = "helios") -> str:
    """Build the consent-screen URL (offline access → refresh token)."""
    params = {
        "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": " ".join(scopes or SCOPES), "access_type": "offline",
        "prompt": "consent", "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def exchange_params(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    return {"code": code, "client_id": client_id, "client_secret": client_secret,
            "redirect_uri": redirect_uri, "grant_type": "authorization_code"}


def refresh_params(refresh_token: str, client_id: str, client_secret: str) -> dict:
    return {"refresh_token": refresh_token, "client_id": client_id,
            "client_secret": client_secret, "grant_type": "refresh_token"}


def _post_token(params: dict) -> dict:
    if requests is None:
        raise GoogleAuthError("requests not installed")
    try:
        r = requests.post(TOKEN_ENDPOINT, data=params, timeout=12)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        raise GoogleAuthError(f"token request failed: {exc}") from exc


def exchange_code(code: str, client_id=None, client_secret=None, redirect_uri=None) -> dict:
    return _post_token(exchange_params(code, client_id or os.environ.get("GOOGLE_CLIENT_ID", ""),
                                       client_secret or os.environ.get("GOOGLE_CLIENT_SECRET", ""),
                                       redirect_uri or os.environ.get("GOOGLE_REDIRECT_URI", "")))


def refresh_access_token(refresh_token: str, client_id=None, client_secret=None) -> dict:
    return _post_token(refresh_params(refresh_token, client_id or os.environ.get("GOOGLE_CLIENT_ID", ""),
                                      client_secret or os.environ.get("GOOGLE_CLIENT_SECRET", "")))


class GoogleClient:
    """Authenticated REST client. Pass an access token (from refresh)."""

    GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
    CAL = "https://www.googleapis.com/calendar/v3"
    TASKS = "https://tasks.googleapis.com/tasks/v1"

    def __init__(self, access_token: str):
        self.token = access_token

    def _get(self, url: str, params: Optional[dict] = None) -> dict:
        if requests is None:
            raise GoogleAuthError("requests not installed")
        try:
            r = requests.get(url, params=params, headers={"Authorization": f"Bearer {self.token}"}, timeout=12)
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001
            raise GoogleAuthError(f"GET {url}: {exc}") from exc

    def _post(self, url: str, body: dict) -> dict:
        if requests is None:
            raise GoogleAuthError("requests not installed")
        try:
            r = requests.post(url, json=body, headers={"Authorization": f"Bearer {self.token}"}, timeout=12)
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001
            raise GoogleAuthError(f"POST {url}: {exc}") from exc

    def list_emails(self, query: str = "is:unread", limit: int = 15) -> list[dict]:
        listing = self._get(f"{self.GMAIL}/messages", {"q": query, "maxResults": limit})
        out = []
        for m in listing.get("messages", []) or []:
            full = self._get(f"{self.GMAIL}/messages/{m['id']}", {"format": "full"})
            out.append(normalize_gmail(full))
        return out

    def list_events(self, time_min: str, time_max: str) -> list[dict]:
        data = self._get(f"{self.CAL}/calendars/primary/events",
                         {"timeMin": time_min, "timeMax": time_max, "singleEvents": "true", "orderBy": "startTime"})
        return [normalize_gcal_event(e) for e in data.get("items", []) or []]

    def create_event(self, summary: str, start_iso: str, end_iso: str, **extra) -> dict:
        body = {"summary": summary, "start": {"dateTime": start_iso}, "end": {"dateTime": end_iso}, **extra}
        return normalize_gcal_event(self._post(f"{self.CAL}/calendars/primary/events", body))
