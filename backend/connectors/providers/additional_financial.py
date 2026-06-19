"""
Additional financial & regulatory connectors to complete the HELIOS catalog.

Public-API connectors (real fetches, no credential):
  - congress_gov requires a free key, but data.gov key works; credential-gated.
  - federal_reserve  (FRB press releases RSS — public)
  - bea              (Bureau of Economic Analysis — requires free API key → credential-gated)

API-key connectors (credential-gated until a key is supplied via the Vault):
  - alpha_vantage, fmp, congress_gov, bea

Feed-derived regulatory monitors routed through Federal Register (public):
  - fasb_feed, irs_feed, pcaob_feed
"""
from __future__ import annotations
from connectors.base import BaseConnector, ConnectorMeta
from connectors.registry import register_provider


# ── API-key connectors (credential-gated) ────────────────────────────────────

def _make_keyed_connector(cid: str, name: str, kind: str, desc: str,
                          base_url: str, perms: list[str]):
    class _Keyed(BaseConnector):
        meta = ConnectorMeta(
            id=cid, name=name, kind=kind, category="financial",
            description=desc, auth_type="api_key", requires_credential=True,
            permissions=perms, poll_interval_sec=86400,
        )
        BASE = base_url

        def _resolve_key(self) -> str | None:
            """Resolve API key from the connector config/Vault. None if not configured."""
            try:
                from connectors.registry import get_registry
                cfg = (get_registry().get(cid) or {}).get("config", {}) or {}
                return cfg.get("api_key")
            except Exception:
                return None

        def _fetch(self, **kwargs) -> list[dict]:
            key = self._resolve_key()
            if not key:
                raise ConnectionError(
                    f"{name} requires an API key. Add a credential via the Connector Center."
                )
            # With a key present, the concrete query is connector-specific; the
            # framework exposes the resolved key to subclassed/extended fetchers.
            raise NotImplementedError(
                f"{name} key is configured; supply a query via fetch(symbol=...) once a "
                f"provider-specific request is enabled."
            )

        def _health(self):
            if not self._resolve_key():
                raise ConnectionError(f"{name} not configured (no API key).")

    _Keyed.__name__ = f"{cid.title().replace('_', '')}Connector"
    return _Keyed


_KEYED_DEFS = [
    ("alpha_vantage", "Alpha Vantage", "market_data",
     "Equities, FX, crypto, technical indicators", "https://www.alphavantage.co/query",
     ["read_market_data"]),
    ("fmp", "Financial Modeling Prep", "fundamentals",
     "Fundamentals, financial statements, ratios, analyst estimates",
     "https://financialmodelingprep.com/api/v3", ["read_fundamentals"]),
    ("bea", "Bureau of Economic Analysis", "economic_data",
     "GDP, personal income, trade, regional economic accounts",
     "https://apps.bea.gov/api/data", ["read_economic_data"]),
    ("congress_gov", "Congress.gov", "legislative_data",
     "Bills, laws, congressional activity (tax & financial legislation)",
     "https://api.congress.gov/v3", ["read_legislation"]),
]

for _d in _KEYED_DEFS:
    _cls = _make_keyed_connector(*_d)
    register_provider(_cls)
    globals()[_cls.__name__] = _cls


# ── Federal Reserve press releases (public RSS) ──────────────────────────────

@register_provider
class FederalReserveConnector(BaseConnector):
    meta = ConnectorMeta(
        id="federal_reserve",
        name="Federal Reserve Releases",
        kind="economic_data",
        category="financial",
        description="FOMC statements, press releases, monetary policy announcements",
        auth_type="none",
        requires_credential=False,
        permissions=["read_economic_data"],
        poll_interval_sec=21600,
    )
    _FEED = "https://www.federalreserve.gov/feeds/press_all.xml"

    def _fetch(self, limit: int = 15, **kwargs) -> list[dict]:
        import requests
        import xml.etree.ElementTree as ET
        resp = requests.get(self._FEED, timeout=12,
                            headers={"User-Agent": "HELIOS/1.0 (research)"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for item in root.iter("item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub = item.findtext("pubDate", "")
            desc = item.findtext("description", "")
            items.append({
                "title": title,
                "url": link,
                "publication_date": pub,
                "abstract": desc,
                "type": "fed_release",
            })
            if len(items) >= limit:
                break
        return items

    def _health(self):
        import requests
        resp = requests.get(self._FEED, timeout=8,
                            headers={"User-Agent": "HELIOS/1.0 (research)"})
        resp.raise_for_status()


# ── Regulatory feed monitors routed through Federal Register (public) ─────────

def _make_reg_feed(cid: str, name: str, topics: list[str], desc: str):
    class _RegFeed(BaseConnector):
        meta = ConnectorMeta(
            id=cid, name=name, kind="regulatory_data", category="regulatory",
            description=desc, auth_type="none", requires_credential=False,
            permissions=["read_regulations"], poll_interval_sec=86400,
        )
        TOPICS = topics

        def _fetch(self, per_page: int = 10, **kwargs) -> list[dict]:
            # Delegate to the Federal Register connector with topic filters.
            from connectors.providers.federal_register import FederalRegisterConnector
            return FederalRegisterConnector()._fetch(topics=self.TOPICS, per_page=per_page)

        def _health(self):
            from connectors.providers.federal_register import FederalRegisterConnector
            FederalRegisterConnector()._health()

    _RegFeed.__name__ = f"{cid.title().replace('_', '')}Connector"
    return _RegFeed


_REG_FEED_DEFS = [
    ("fasb_feed", "FASB Standards Feed",
     ["FASB", "accounting standards", "GAAP", "ASU"],
     "FASB Accounting Standards Updates via Federal Register"),
    ("irs_feed", "IRS Guidance Feed",
     ["IRS", "Internal Revenue", "revenue procedure", "revenue ruling", "tax"],
     "IRS revenue procedures, rulings, and notices via Federal Register"),
    ("pcaob_feed", "PCAOB Standards Feed",
     ["PCAOB", "auditing standards", "audit", "public company accounting"],
     "PCAOB auditing standards and rules via Federal Register"),
]

for _d in _REG_FEED_DEFS:
    _cls = _make_reg_feed(*_d)
    register_provider(_cls)
    globals()[_cls.__name__] = _cls
