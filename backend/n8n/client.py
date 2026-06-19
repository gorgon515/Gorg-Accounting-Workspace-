"""N8N REST client — real connectivity to a local/remote N8N instance.

Targets the N8N public API (``/api/v1``) with the ``X-N8N-API-KEY`` header. All
network calls are guarded: when N8N is unreachable or unconfigured they raise
``N8NUnavailable`` so the API/agents degrade gracefully. URL/header construction
is pure and unit-tested; the live calls work against a real N8N on the user's box
(set N8N_URL and N8N_API_KEY).
"""
from __future__ import annotations

import os
from typing import Optional

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore


class N8NUnavailable(RuntimeError):
    pass


class N8NClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("N8N_URL", "http://127.0.0.1:5678")).rstrip("/")
        self.api_key = api_key or os.environ.get("N8N_API_KEY", "")

    # ---- pure helpers (unit-tested, no network) ----
    @property
    def headers(self) -> dict:
        h = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            h["X-N8N-API-KEY"] = self.api_key
        return h

    def url(self, path: str) -> str:
        return f"{self.base_url}/api/v1/{path.lstrip('/')}"

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    # ---- live calls (network-guarded) ----
    def _request(self, method: str, path: str, body: Optional[dict] = None, params: Optional[dict] = None):
        if requests is None:
            raise N8NUnavailable("requests not installed")
        try:
            r = requests.request(method, self.url(path), headers=self.headers, json=body, params=params, timeout=10)
            r.raise_for_status()
            return r.json() if r.content else {}
        except Exception as exc:  # noqa: BLE001
            raise N8NUnavailable(f"{method} {path}: {exc}") from exc

    def status(self) -> dict:
        if not self.configured:
            return {"connected": False, "reason": "N8N_API_KEY not set", "url": self.base_url}
        try:
            wf = self._request("GET", "workflows", params={"limit": 1})
            return {"connected": True, "url": self.base_url, "workflows_visible": len(wf.get("data", wf) or [])}
        except N8NUnavailable as exc:
            return {"connected": False, "reason": str(exc), "url": self.base_url}

    def list_workflows(self) -> list:
        data = self._request("GET", "workflows")
        return data.get("data", data) if isinstance(data, dict) else data

    def get_workflow(self, workflow_id: str) -> dict:
        return self._request("GET", f"workflows/{workflow_id}")

    def create_workflow(self, workflow: dict) -> dict:
        return self._request("POST", "workflows", body=workflow)

    def activate(self, workflow_id: str) -> dict:
        return self._request("POST", f"workflows/{workflow_id}/activate")

    def deactivate(self, workflow_id: str) -> dict:
        return self._request("POST", f"workflows/{workflow_id}/deactivate")

    def list_executions(self, workflow_id: Optional[str] = None, limit: int = 20) -> list:
        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        data = self._request("GET", "executions", params=params)
        return data.get("data", data) if isinstance(data, dict) else data

    def get_execution(self, execution_id: str) -> dict:
        """Execution detail — status, timing, and node run data (logs)."""
        return self._request("GET", f"executions/{execution_id}", params={"includeData": "true"})

    def run_via_webhook(self, webhook_path: str, payload: Optional[dict] = None) -> dict:
        """Trigger a workflow that starts with a Webhook node (programmatic run)."""
        if requests is None:
            raise N8NUnavailable("requests not installed")
        try:
            r = requests.post(f"{self.base_url}/webhook/{webhook_path.lstrip('/')}", json=payload or {}, timeout=15)
            r.raise_for_status()
            return r.json() if r.content else {"ok": True}
        except Exception as exc:  # noqa: BLE001
            raise N8NUnavailable(f"webhook {webhook_path}: {exc}") from exc
