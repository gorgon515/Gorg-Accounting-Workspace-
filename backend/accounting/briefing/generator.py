"""Accounting daily-briefing generator.

Synthesizes a structured briefing from stored intel items (real data from the
collectors). Deterministic and rule-based — the brain can narrate it, but the
engine itself produces the structure from facts, with a confidence level driven
by source coverage. No LLM call required here, so it is fully testable.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

# Keyword → industry mapping for "affected industries".
_INDUSTRY = {
    "Financial institutions": ["bank", "credit loss", "cecl", "loan", "deposit", "326"],
    "Insurance": ["insurance", "insurer", "long-duration", "944"],
    "Software & technology": ["software", "saas", "cloud", "internal-use", "606", "350-40"],
    "Real estate": ["lease", "842", "real estate", "reit"],
    "Energy & utilities": ["energy", "oil", "gas", "utility", "power"],
    "Crypto & digital assets": ["crypto", "digital asset", "bitcoin", "350-60"],
    "Healthcare": ["healthcare", "hospital", "pharma", "life sciences"],
}

# ASC topic → CPA exam section (which exam an update most affects).
_ASC_EXAM = {
    "606": "FAR — revenue recognition", "842": "FAR — leases",
    "326": "FAR/AUD — credit losses (CECL)", "350": "FAR — goodwill & intangibles",
    "718": "FAR/REG — stock compensation", "740": "FAR/REG — income taxes",
}

_RISK_WORDS = ["material weakness", "restatement", "fraud", "going concern", "impairment",
               "non-compliance", "enforcement", "deficiency"]

_DOC_PRIORITY = {
    "Accounting Standards Update": 0, "Exposure Draft": 1, "Proposed Rule": 2,
    "SEC Release": 3, "PCAOB Release": 4, "IRS Notice": 5,
    "Revenue Ruling": 6, "Revenue Procedure": 7, "Press Release": 8, "Other": 9,
}


def _industries(items: list[dict]) -> list[str]:
    found = set()
    for it in items:
        blob = f"{it.get('title','')} {it.get('summary','')} {' '.join(it.get('asc_codes',[]))}".lower()
        for industry, kws in _INDUSTRY.items():
            if any(k in blob for k in kws):
                found.add(industry)
    return sorted(found)


def _cpa_impact(items: list[dict]) -> list[dict]:
    out = []
    seen = set()
    for it in items:
        for code in it.get("asc_codes", []):
            if code in _ASC_EXAM and code not in seen:
                seen.add(code)
                out.append({"asc": f"ASC {code}", "exam": _ASC_EXAM[code], "driver": it.get("title", "")})
    return out


def _emerging_risks(items: list[dict]) -> list[dict]:
    risks = []
    for it in items:
        blob = f"{it.get('title','')} {it.get('summary','')}".lower()
        hits = [w for w in _RISK_WORDS if w in blob]
        if hits:
            risks.append({"signal": hits, "title": it.get("title", ""), "source": it.get("source")})
    return risks


def _action_items(key_changes: list[dict], upcoming: list[dict]) -> list[str]:
    actions = []
    for it in key_changes[:5]:
        dt = it.get("doc_type", "")
        if dt == "Accounting Standards Update":
            actions.append(f"Assess adoption impact of {it.get('asu_number') or it['title']}.")
        elif dt == "Exposure Draft":
            actions.append(f"Review exposure draft and consider a comment letter: {it['title']}.")
        elif dt in ("Proposed Rule", "SEC Release"):
            actions.append(f"Evaluate SEC development for disclosure impact: {it['title']}.")
        elif dt in ("IRS Notice", "Revenue Ruling", "Revenue Procedure"):
            actions.append(f"Check tax-position impact: {it['title']}.")
    for it in upcoming[:3]:
        actions.append(f"Prepare for effective date {it['effective_date']}: {it['title']}.")
    return actions


def _confidence(items: list[dict], source_errors: Optional[dict]) -> dict:
    sources = {it.get("source") for it in items}
    n_sources = len(sources)
    n_err = len(source_errors or {})
    if n_sources >= 3 and n_err == 0:
        level = "High"
    elif n_sources >= 2:
        level = "Medium"
    elif n_sources >= 1:
        level = "Low"
    else:
        level = "None"
    return {
        "level": level,
        "sources_represented": sorted(s for s in sources if s),
        "source_errors": source_errors or {},
        "rationale": f"{len(items)} items across {n_sources} source(s); {n_err} source(s) unreachable.",
    }


def generate_briefing(items: list[dict], *, new_ids: Optional[list[str]] = None,
                      today: Optional[str] = None, source_errors: Optional[dict] = None) -> dict:
    today = today or date.today().isoformat()
    new_ids = set(new_ids or [])

    new_dev = [it for it in items if it.get("id") in new_ids] if new_ids else \
        [it for it in items if (it.get("first_seen") or "")[:10] == today]
    key_changes = sorted(items, key=lambda it: _DOC_PRIORITY.get(it.get("doc_type", "Other"), 9))[:8]
    upcoming = sorted([it for it in items if it.get("effective_date") and it["effective_date"] >= today],
                      key=lambda it: it["effective_date"])
    industries = _industries(items)
    cpa = _cpa_impact(items)
    risks = _emerging_risks(items)

    n_asu = sum(1 for it in items if it.get("doc_type") == "Accounting Standards Update")
    n_ed = sum(1 for it in items if it.get("doc_type") == "Exposure Draft")
    summary = (
        f"{len(new_dev)} new development(s) today across {len(set(it.get('source') for it in items))} source(s): "
        f"{n_asu} ASU(s), {n_ed} exposure draft(s), {len(upcoming)} upcoming effective date(s). "
        + (f"Affected industries: {', '.join(industries)}. " if industries else "")
        + (f"{len(risks)} emerging-risk signal(s) flagged." if risks else "No elevated risk signals.")
    )

    return {
        "date": today,
        "executive_summary": summary,
        "new_developments": [_brief(it) for it in new_dev[:10]],
        "key_changes": [_brief(it) for it in key_changes],
        "upcoming_effective_dates": [_brief(it) for it in upcoming[:10]],
        "affected_industries": industries,
        "cpa_impact": cpa,
        "emerging_risks": risks,
        "action_items": _action_items(key_changes, upcoming),
        "confidence": _confidence(items, source_errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _brief(it: dict) -> dict:
    return {
        "source": it.get("source"),
        "doc_type": it.get("doc_type"),
        "title": it.get("title"),
        "url": it.get("url"),
        "published": it.get("published"),
        "effective_date": it.get("effective_date"),
        "asc_codes": it.get("asc_codes", []),
    }
