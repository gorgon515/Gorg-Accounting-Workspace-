"""FASB collector — Accounting Standards Updates and exposure drafts.

FASB's RSS endpoints occasionally change; override with HELIOS_FEEDS_FASB
(comma-separated URLs) if needed. The collector and parser are stable regardless.
"""
from __future__ import annotations

from ..schemas import DocType, Source
from .base import Collector, _env_feeds


class FASBCollector(Collector):
    source = Source.FASB.value
    feeds = _env_feeds("HELIOS_FEEDS_FASB", [
        ("https://www.fasb.org/page/rssfeed?feed=ASU", DocType.ASU),
        ("https://www.fasb.org/page/rssfeed?feed=ED", DocType.EXPOSURE_DRAFT),
    ])
