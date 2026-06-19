"""
Federal Register connector — free public API, no auth required.
https://www.federalregister.gov/developers/api/v1
"""
from __future__ import annotations
from connectors.base import BaseConnector, ConnectorMeta
from connectors.registry import register_provider

_BASE = "https://www.federalregister.gov/api/v1"


@register_provider
class FederalRegisterConnector(BaseConnector):
    meta = ConnectorMeta(
        id="federal_register",
        name="Federal Register",
        kind="regulatory_data",
        category="regulatory",
        description="Federal regulations, proposed rules, IRS notices via Federal Register API",
        auth_type="none",
        requires_credential=False,
        permissions=["read_regulations"],
        poll_interval_sec=86400,
    )

    def _fetch(self, topics: list[str] | None = None, per_page: int = 10,
               agencies: list[str] | None = None) -> list[dict]:
        import requests
        params: dict = {
            "per_page": per_page,
            "order": "newest",
            "fields[]": ["title", "abstract", "document_number", "publication_date",
                         "type", "agency_names", "html_url"],
        }
        if topics:
            params["conditions[term]"] = " OR ".join(topics)
        if agencies:
            params["conditions[agency_ids][]"] = agencies
        resp = requests.get(f"{_BASE}/documents.json", params=params, timeout=12)
        resp.raise_for_status()
        docs = resp.json().get("results", [])
        return [{
            "title": d.get("title", ""),
            "document_number": d.get("document_number", ""),
            "publication_date": d.get("publication_date", ""),
            "type": d.get("type", ""),
            "agencies": d.get("agency_names", []),
            "abstract": d.get("abstract", ""),
            "url": d.get("html_url", ""),
        } for d in docs]

    def _health(self):
        import requests
        resp = requests.get(f"{_BASE}/documents.json", params={"per_page": 1}, timeout=8)
        resp.raise_for_status()

    def fetch_tax_updates(self, per_page: int = 10) -> list[dict]:
        return self._fetch(topics=["tax", "IRS", "revenue procedure"], per_page=per_page)

    def fetch_accounting_updates(self, per_page: int = 10) -> list[dict]:
        return self._fetch(topics=["accounting standards", "FASB", "GAAP", "PCAOB"], per_page=per_page)

    def fetch_sec_rules(self, per_page: int = 10) -> list[dict]:
        return self._fetch(topics=["securities", "SEC", "disclosure"], per_page=per_page)
