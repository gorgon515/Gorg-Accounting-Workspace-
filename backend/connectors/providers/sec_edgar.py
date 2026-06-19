"""
SEC EDGAR connector — free public API, no auth required.
Endpoints: https://data.sec.gov/  (EDGAR XBRL/Submissions APIs)
"""
from __future__ import annotations
from connectors.base import BaseConnector, ConnectorMeta, FetchResult
from connectors.registry import register_provider

_HEADERS = {"User-Agent": "HELIOS/1.0 (contact@helios.local)"}


@register_provider
class SECEdgarConnector(BaseConnector):
    meta = ConnectorMeta(
        id="sec_edgar",
        name="SEC EDGAR",
        kind="financial_data",
        category="financial",
        description="SEC filings, XBRL submissions, company facts via public EDGAR API",
        auth_type="none",
        requires_credential=False,
        permissions=["read_filings", "read_fundamentals"],
        poll_interval_sec=3600,
    )

    def _fetch(self, cik: str = "0000320193", form_type: str = "10-K", limit: int = 5) -> list[dict]:
        import requests
        cik_padded = str(cik).lstrip("0").zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        acc_nos = filings.get("accessionNumber", [])
        docs = filings.get("primaryDocument", [])
        results = []
        for i, form in enumerate(forms):
            if form_type and form != form_type:
                continue
            results.append({
                "cik": cik,
                "entity": data.get("name", ""),
                "form": form,
                "filing_date": dates[i] if i < len(dates) else "",
                "accession_number": acc_nos[i] if i < len(acc_nos) else "",
                "primary_doc": docs[i] if i < len(docs) else "",
            })
            if len(results) >= limit:
                break
        return results

    def _health(self):
        import requests
        resp = requests.get("https://data.sec.gov/submissions/CIK0000320193.json",
                            headers=_HEADERS, timeout=8)
        resp.raise_for_status()

    def fetch_company_facts(self, cik: str) -> dict:
        import requests
        cik_padded = str(cik).lstrip("0").zfill(10)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def search_fulltext(self, query: str, date_range: str = "", limit: int = 10) -> list[dict]:
        import requests
        url = "https://efts.sec.gov/LATEST/search-index"
        params = {"q": f'"{query}"', "dateRange": date_range, "hits.hits.total.value": limit}
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        return [h.get("_source", {}) for h in hits[:limit]]
