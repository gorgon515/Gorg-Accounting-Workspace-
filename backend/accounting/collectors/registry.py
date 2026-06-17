"""The set of active collectors and a helper to run them all."""
from __future__ import annotations

from .base import Collector, run_all
from .fasb import FASBCollector
from .irs import IRSCollector
from .pcaob import PCAOBCollector
from .sec import SECCollector

ALL_COLLECTORS: list[Collector] = [
    FASBCollector(),
    SECCollector(),
    PCAOBCollector(),
    IRSCollector(),
]


def collect_all():
    """Live-collect from every source; returns (items, {source: error})."""
    return run_all(ALL_COLLECTORS)
