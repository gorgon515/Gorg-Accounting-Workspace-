"""IRS collector — IRS Newswire / guidance (notices, rulings, procedures)."""
from __future__ import annotations

from ..schemas import DocType, Source
from .base import Collector, _env_feeds


class IRSCollector(Collector):
    source = Source.IRS.value
    feeds = _env_feeds("HELIOS_FEEDS_IRS", [
        ("https://www.irs.gov/newsroom/irs-guidance/feed", DocType.IRS_NOTICE),
        ("https://www.irs.gov/newsroom/feed", DocType.PRESS),
    ])
