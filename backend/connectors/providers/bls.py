"""
Bureau of Labor Statistics connector — free public API.
https://www.bls.gov/developers/api_signature_v2.htm
"""
from __future__ import annotations
import json
from connectors.base import BaseConnector, ConnectorMeta
from connectors.registry import register_provider

_BASE = "https://api.bls.gov/publicAPI/v2"

BLS_SERIES = {
    "CPI_ALL": "CUSR0000SA0",          # CPI All Urban Consumers
    "CPI_CORE": "CUSR0000SA0L1E",      # CPI Less Food and Energy
    "UNEMPLOYMENT": "LNS14000000",     # Unemployment Rate
    "NONFARM_PAYROLL": "CES0000000001",# Total Nonfarm Payrolls
    "AVG_HOURLY_EARNINGS": "CES0500000003",  # Avg Hourly Earnings
    "PPI": "WPUFD49104",               # Producer Price Index
}


@register_provider
class BLSConnector(BaseConnector):
    meta = ConnectorMeta(
        id="bls",
        name="Bureau of Labor Statistics",
        kind="economic_data",
        category="financial",
        description="CPI, unemployment, payrolls, wages, PPI from BLS",
        auth_type="api_key",
        requires_credential=False,
        permissions=["read_economic_data"],
        poll_interval_sec=86400,
    )

    def _get_api_key(self) -> str | None:
        try:
            from connectors.db import get_connection
            conn = get_connection()
            row = conn.execute(
                "SELECT vault_key FROM connector_credential WHERE connector_id='bls'"
            ).fetchone()
            conn.close()
            if row:
                return row["vault_key"]
        except Exception:
            pass
        return None

    def _fetch(self, series_ids: list[str] | None = None, years: int = 2) -> list[dict]:
        import requests
        from datetime import datetime
        ids = series_ids or list(BLS_SERIES.values())[:5]
        end_year = datetime.now().year
        start_year = end_year - years
        payload = {
            "seriesid": ids,
            "startyear": str(start_year),
            "endyear": str(end_year),
        }
        api_key = self._get_api_key()
        if api_key:
            payload["registrationkey"] = api_key
        resp = requests.post(f"{_BASE}/timeseries/data/", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for series in data.get("Results", {}).get("series", []):
            obs = series.get("data", [])
            results.append({
                "series_id": series["seriesID"],
                "latest": obs[0] if obs else {},
                "observations": obs[:24],
            })
        return results

    def _health(self):
        import requests
        resp = requests.post(f"{_BASE}/timeseries/data/", json={
            "seriesid": ["LNS14000000"], "startyear": "2024", "endyear": "2024"
        }, timeout=8)
        resp.raise_for_status()
