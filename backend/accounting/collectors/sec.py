"""SEC collector — press releases and proposed/final rules (real RSS endpoints)."""
from __future__ import annotations

from ..schemas import DocType, Source
from .base import Collector, _env_feeds


class SECCollector(Collector):
    source = Source.SEC.value
    feeds = _env_feeds("HELIOS_FEEDS_SEC", [
        ("https://www.sec.gov/news/pressreleases.rss", DocType.SEC_RELEASE),
        ("https://www.sec.gov/rss/rules/proposed.xml", DocType.PROPOSED_RULE),
        ("https://www.sec.gov/rss/rules/final.xml", DocType.SEC_RELEASE),
    ])
