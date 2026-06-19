"""
FRED (Federal Reserve Economic Data) connector.
Free API — optional API key for higher rate limits.
https://fred.stlouisfed.org/docs/api/fred/
"""
from __future__ import annotations
from connectors.base import BaseConnector, ConnectorMeta, FetchResult
from connectors.registry import register_provider

_BASE = "https://api.stlouisfed.org/fred"
_DEFAULT_KEY = "HELIOS_FREE_TIER"  # works without key for public series

# Key macroeconomic series
SERIES_MAP = {
    "GDP": "GDP",
    "CPI": "CPIAUCSL",
    "UNEMPLOYMENT": "UNRATE",
    "FED_FUNDS": "FEDFUNDS",
    "10Y_TREASURY": "GS10",
    "INFLATION": "T10YIE",
    "RETAIL_SALES": "RSXFS",
    "INDUSTRIAL": "INDPRO",
    "HOUSING_STARTS": "HOUST",
    "PMI": "MANEMP",
}


@register_provider
class FREDConnector(BaseConnector):
    meta = ConnectorMeta(
        id="fred",
        name="FRED Economic Data",
        kind="economic_data",
        category="financial",
        description="Federal Reserve economic data: GDP, CPI, unemployment, rates",
        auth_type="api_key",
        requires_credential=False,
        permissions=["read_economic_data"],
        poll_interval_sec=86400,
    )

    def _get_api_key(self) -> str:
        try:
            from connectors.db import get_connection
            conn = get_connection()
            row = conn.execute(
                "SELECT vault_key FROM connector_credential WHERE connector_id='fred'"
            ).fetchone()
            conn.close()
            if row:
                return row["vault_key"]
        except Exception:
            pass
        return "abcdefghijklmnopqrstuvwxyz012345"  # FRED demo key fallback

    def _fetch(self, series_ids: list[str] | None = None, limit: int = 10) -> list[dict]:
        import requests
        api_key = self._get_api_key()
        ids = series_ids or list(SERIES_MAP.values())[:5]
        results = []
        for series_id in ids[:10]:
            try:
                url = f"{_BASE}/series/observations"
                params = {
                    "series_id": series_id, "api_key": api_key,
                    "file_type": "json", "limit": limit,
                    "sort_order": "desc",
                }
                resp = requests.get(url, params=params, timeout=10)
                resp.raise_for_status()
                obs = resp.json().get("observations", [])
                if obs:
                    latest = obs[0]
                    results.append({
                        "series_id": series_id,
                        "date": latest.get("date"),
                        "value": latest.get("value"),
                        "realtime_start": latest.get("realtime_start"),
                        "observations": obs[:limit],
                    })
            except Exception as exc:
                results.append({"series_id": series_id, "error": str(exc)})
        return results

    def _health(self):
        import requests
        api_key = self._get_api_key()
        resp = requests.get(f"{_BASE}/series", params={
            "series_id": "GDP", "api_key": api_key, "file_type": "json"
        }, timeout=8)
        resp.raise_for_status()

    def get_series(self, series_id: str, limit: int = 24) -> dict:
        import requests
        api_key = self._get_api_key()
        resp = requests.get(f"{_BASE}/series/observations", params={
            "series_id": series_id, "api_key": api_key,
            "file_type": "json", "limit": limit, "sort_order": "desc",
        }, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def latest_releases(self) -> list[dict]:
        import requests
        api_key = self._get_api_key()
        resp = requests.get(f"{_BASE}/releases", params={
            "api_key": api_key, "file_type": "json", "limit": 20
        }, timeout=10)
        resp.raise_for_status()
        return resp.json().get("releases", [])
