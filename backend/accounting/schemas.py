"""Normalized schemas for accounting-intelligence items.

A single ``IntelItem`` shape regardless of source (FASB/SEC/PCAOB/IRS/...), with a
stable id for de-duplication and historical tracking, plus heuristics that
classify a raw feed entry into a document type.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional


class Source(str, Enum):
    FASB = "FASB"
    SEC = "SEC"
    PCAOB = "PCAOB"
    IRS = "IRS"
    TREASURY = "Treasury"
    AICPA = "AICPA"


class DocType(str, Enum):
    ASU = "Accounting Standards Update"
    EXPOSURE_DRAFT = "Exposure Draft"
    PROPOSED_RULE = "Proposed Rule"
    SEC_RELEASE = "SEC Release"
    PCAOB_RELEASE = "PCAOB Release"
    IRS_NOTICE = "IRS Notice"
    REVENUE_RULING = "Revenue Ruling"
    REVENUE_PROCEDURE = "Revenue Procedure"
    PRESS = "Press Release"
    OTHER = "Other"


# Title-keyword → DocType heuristics (ordered; first match wins).
_CLASSIFIERS: list[tuple[re.Pattern, DocType]] = [
    (re.compile(r"\bASU\b|accounting standards update", re.I), DocType.ASU),
    (re.compile(r"exposure draft|\bED\b", re.I), DocType.EXPOSURE_DRAFT),
    (re.compile(r"revenue ruling|rev\.?\s*rul", re.I), DocType.REVENUE_RULING),
    (re.compile(r"revenue procedure|rev\.?\s*proc", re.I), DocType.REVENUE_PROCEDURE),
    (re.compile(r"\bnotice\b", re.I), DocType.IRS_NOTICE),
    (re.compile(r"propos(?:e|es|ed|ing|al)", re.I), DocType.PROPOSED_RULE),
    (re.compile(r"pcaob", re.I), DocType.PCAOB_RELEASE),
]

_ASC_RE = re.compile(r"\bASC\s?(\d{3})\b", re.I)
_ASU_RE = re.compile(r"\bASU\s?(No\.?\s?)?(\d{4}-\d{2})\b", re.I)
_EFFECTIVE_RE = re.compile(r"effective\s+(?:for\s+)?(?:fiscal\s+years?\s+)?(?:beginning\s+)?(?:after\s+)?"
                           r"([A-Z][a-z]+ \d{1,2},? \d{4}|\d{4})", re.I)


def classify(title: str, default: DocType = DocType.OTHER) -> DocType:
    for pat, dt in _CLASSIFIERS:
        if pat.search(title or ""):
            return dt
    return default


def extract_asc_codes(text: str) -> list[str]:
    return sorted({m.group(1) for m in _ASC_RE.finditer(text or "")})


def extract_asu_number(text: str) -> Optional[str]:
    m = _ASU_RE.search(text or "")
    return m.group(2) if m else None


def _coerce_date(value: Optional[str]) -> Optional[str]:
    """Best-effort parse of common feed date formats → ISO YYYY-MM-DD."""
    if not value:
        return None
    value = value.strip()
    fmts = ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%B %d, %Y", "%m/%d/%Y"]
    for f in fmts:
        try:
            return datetime.strptime(value, f).date().isoformat()
        except ValueError:
            continue
    # Last resort: a leading ISO date.
    m = re.match(r"(\d{4}-\d{2}-\d{2})", value)
    return m.group(1) if m else None


@dataclass
class IntelItem:
    source: str
    title: str
    url: str
    doc_type: str = DocType.OTHER.value
    summary: str = ""
    published: Optional[str] = None       # ISO date
    effective_date: Optional[str] = None  # ISO date if detected
    asc_codes: list[str] = field(default_factory=list)
    asu_number: Optional[str] = None
    guid: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def id(self) -> str:
        key = f"{self.source}|{self.guid or self.url or self.title}"
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        return d

    @classmethod
    def from_feed_entry(cls, source: str, entry: dict, default_type: DocType = DocType.OTHER) -> "IntelItem":
        """Build a normalized item from a parsed RSS/Atom entry dict."""
        title = (entry.get("title") or "").strip()
        text = f"{title} {entry.get('summary', '')}"
        eff = _EFFECTIVE_RE.search(entry.get("summary", "") or "")
        return cls(
            source=source,
            title=title,
            url=(entry.get("link") or "").strip(),
            doc_type=classify(title, default_type).value,
            summary=(entry.get("summary") or "").strip()[:1200],
            published=_coerce_date(entry.get("published")),
            effective_date=_coerce_date(eff.group(1)) if eff else None,
            asc_codes=extract_asc_codes(text),
            asu_number=extract_asu_number(text),
            guid=entry.get("guid") or entry.get("link"),
        )


def upcoming_effective(items: list[IntelItem], today: Optional[date] = None) -> list[IntelItem]:
    today = today or date.today()
    out = []
    for it in items:
        if it.effective_date:
            try:
                if date.fromisoformat(it.effective_date) >= today:
                    out.append(it)
            except ValueError:
                pass
    return sorted(out, key=lambda i: i.effective_date or "")
