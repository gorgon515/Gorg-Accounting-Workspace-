"""PCAOB collector — releases and news (real RSS; override via HELIOS_FEEDS_PCAOB)."""
from __future__ import annotations

from ..schemas import DocType, Source
from .base import Collector, _env_feeds


class PCAOBCollector(Collector):
    source = Source.PCAOB.value
    feeds = _env_feeds("HELIOS_FEEDS_PCAOB", [
        ("https://pcaobus.org/feed", DocType.PCAOB_RELEASE),
    ])
