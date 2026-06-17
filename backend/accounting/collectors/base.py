"""Collector base: real HTTP fetching of standard-setter feeds.

Live network calls hit the real endpoints (with an SEC fair-access-compliant
User-Agent). They are network-guarded — a failed/blocked fetch raises
``SourceUnavailable`` so the registry can skip that source and the API can report
it, rather than crashing. Parsing is delegated to the unit-tested feed parser, so
``collect_from_xml`` lets tests exercise the full pipeline offline.
"""
from __future__ import annotations

import os
import urllib.request
from typing import Iterable

from ..parsers import feeds
from ..schemas import DocType, IntelItem

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

# SEC's fair-access policy requires a descriptive UA with contact info.
USER_AGENT = os.environ.get(
    "HELIOS_HTTP_UA", "HELIOS Accounting Intelligence/0.4 (contact: helios@example.com)"
)
ACCEPT = "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"


class SourceUnavailable(RuntimeError):
    """A feed could not be fetched (network blocked, 4xx/5xx, timeout)."""


def http_get(url: str, timeout: int = 12) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept": ACCEPT}
    if requests is not None:
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.text
        except Exception as exc:  # noqa: BLE001
            raise SourceUnavailable(f"{url}: {exc}") from exc
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - fixed feed URLs
            return resp.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        raise SourceUnavailable(f"{url}: {exc}") from exc


def _env_feeds(env_key: str, defaults: list[tuple[str, DocType]]) -> list[tuple[str, DocType]]:
    """Allow overriding/extending feed URLs via env (comma-separated)."""
    override = os.environ.get(env_key)
    if not override:
        return defaults
    dtype = defaults[0][1] if defaults else DocType.OTHER
    return [(u.strip(), dtype) for u in override.split(",") if u.strip()]


class Collector:
    source: str = "Unknown"
    feeds: list[tuple[str, DocType]] = []

    def collect(self) -> list[IntelItem]:
        """Fetch every feed live and return de-duplicated normalized items."""
        items: dict[str, IntelItem] = {}
        errors: list[str] = []
        for url, dtype in self.feeds:
            try:
                xml = http_get(url)
            except SourceUnavailable as exc:
                errors.append(str(exc))
                continue
            for entry in feeds.parse(xml):
                item = IntelItem.from_feed_entry(self.source, entry, dtype)
                if item.title and item.url:
                    items[item.id] = item
        if not items and errors:
            raise SourceUnavailable("; ".join(errors))
        return list(items.values())

    def collect_from_xml(self, xml: str, dtype: DocType = DocType.OTHER) -> list[IntelItem]:
        """Parse an already-fetched document (used by tests with real-format fixtures)."""
        out: list[IntelItem] = []
        for entry in feeds.parse(xml):
            item = IntelItem.from_feed_entry(self.source, entry, dtype)
            if item.title:
                out.append(item)
        return out


def run_all(collectors: Iterable[Collector]) -> tuple[list[IntelItem], dict[str, str]]:
    """Run several collectors; return (items, {source: error}) so one dead source
    never blocks the others."""
    all_items: list[IntelItem] = []
    errors: dict[str, str] = {}
    for c in collectors:
        try:
            all_items.extend(c.collect())
        except SourceUnavailable as exc:
            errors[c.source] = str(exc)
    return all_items, errors
