"""Outlook / Microsoft 365 integration via Microsoft Graph.

OAuth URL + token request construction are pure and unit-tested; Graph message/
event responses normalize to the same shapes as Google (so the intelligence
engines are provider-agnostic). Live calls need an Azure app registration
(OUTLOOK_CLIENT_ID / OUTLOOK_CLIENT_SECRET / OUTLOOK_TENANT).
"""
from __future__ import annotations

import os
import urllib.parse
from typing import Optional

from .schemas import normalize_graph_event, normalize_graph_message

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = ["offline_access", "Mail.Read", "Mail.Send", "Calendars.ReadWrite", "Tasks.ReadWrite"]

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore


class OutlookAuthError(RuntimeError):
    pass


def _authority(tenant: Optional[str] = None) -> str:
    return f"https://login.microsoftonline.com/{tenant or os.environ.get('OUTLOOK_TENANT', 'common')}"


def auth_url(client_id: str, redirect_uri: str, tenant: Optional[str] = None,
             scopes: Optional[list[str]] = None, state: str = "helios") -> str:
    params = {"client_id": client_id, "response_type": "code", "redirect_uri": redirect_uri,
              "response_mode": "query", "scope": " ".join(scopes or SCOPES), "state": state}
    return f"{_authority(tenant)}/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"


def token_endpoint(tenant: Optional[str] = None) -> str:
    return f"{_authority(tenant)}/oauth2/v2.0/token"


def exchange_params(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    return {"code": code, "client_id": client_id, "client_secret": client_secret,
            "redirect_uri": redirect_uri, "grant_type": "authorization_code",
            "scope": " ".join(SCOPES)}


def refresh_params(refresh_token: str, client_id: str, client_secret: str) -> dict:
    return {"refresh_token": refresh_token, "client_id": client_id, "client_secret": client_secret,
            "grant_type": "refresh_token", "scope": " ".join(SCOPES)}


class OutlookClient:
    def __init__(self, access_token: str):
        self.token = access_token

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        if requests is None:
            raise OutlookAuthError("requests not installed")
        try:
            r = requests.get(f"{GRAPH}{path}", params=params,
                             headers={"Authorization": f"Bearer {self.token}"}, timeout=12)
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001
            raise OutlookAuthError(f"GET {path}: {exc}") from exc

    def list_emails(self, limit: int = 15) -> list[dict]:
        data = self._get("/me/messages", {"$top": limit, "$select": "from,toRecipients,subject,bodyPreview,receivedDateTime,isRead"})
        return [normalize_graph_message(m) for m in data.get("value", []) or []]

    def list_events(self, start_iso: str, end_iso: str) -> list[dict]:
        data = self._get("/me/calendarView", {"startDateTime": start_iso, "endDateTime": end_iso})
        return [normalize_graph_event(e) for e in data.get("value", []) or []]
