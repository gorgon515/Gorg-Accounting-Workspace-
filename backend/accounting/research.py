"""Accounting Research Engine (Phase 4 expansion).

Builds on the ASC knowledge base in app.services.accounting_research, adding:
  • a full technical memo (Facts / Issue / Relevant Guidance / Analysis /
    Alternatives / Conclusion / References)
  • implementation checklists
  • ASU summarization grounded in the knowledge base
All grounded in cited topics — no invented citations.
"""
from __future__ import annotations

from typing import Optional

from app.services.accounting_research import ASC_TOPICS, explain_asc, _resolve  # type: ignore

# Generic alternatives surfaced when an ASC involves a recognized policy choice.
_ALTERNATIVES = {
    "606": ["Recognize over time vs. at a point in time (per control transfer)",
            "Principal vs. agent presentation", "Output vs. input method for progress"],
    "842": ["Finance vs. operating lease classification", "Elect the short-term lease exemption",
            "Use the risk-free-rate practical expedient (private companies)"],
    "326": ["Loss-rate vs. discounted-cash-flow vs. probability-of-default method",
            "Pooling segmentation of financial assets"],
    "350": ["Qualitative ('Step 0') assessment vs. quantitative impairment test",
            "Private-company goodwill amortization alternative"],
    "718": ["Estimate forfeitures vs. account for them as they occur",
            "Equity vs. liability classification"],
}


def implementation_checklist(topic: str) -> dict:
    """A practical adoption checklist grounded in the ASC's framework."""
    kb = explain_asc(topic)
    code = _resolve(topic)
    framework = kb.get("framework") or kb.get("key_points", [])
    steps = [
        f"Confirm scope: determine which arrangements fall under {kb['asc']}.",
        "Gather the underlying contracts/data needed to apply the guidance.",
        *[f"Apply: {f}" for f in framework],
        "Identify and document significant judgments and estimates.",
        "Determine required policy elections and practical expedients.",
        "Assess system/process changes needed to capture and compute amounts.",
        f"Draft the required disclosures: {', '.join(kb.get('disclosures', []) ) or 'per the standard'}.",
        "Define the transition approach and any comparative-period restatement.",
        "Coordinate with auditors on judgments and documentation.",
    ]
    return {
        "asc": kb["asc"],
        "title": kb["title"],
        "checklist": steps,
        "policy_choices": _ALTERNATIVES.get(code or "", []),
        "fs_impact": kb.get("fs_impact"),
        "cpa_exam_impact": kb.get("cpa_exam"),
    }


def technical_memo(facts: str, issue: str, topic: str, *,
                   alternatives: Optional[list[str]] = None,
                   conclusion: Optional[str] = None) -> dict:
    """Full technical memo in the Facts/Issue/Guidance/Analysis/Alternatives/
    Conclusion/References structure."""
    if not facts or not facts.strip():
        raise ValueError("facts are required")
    if not issue or not issue.strip():
        raise ValueError("issue is required")
    kb = explain_asc(topic)  # raises if unknown — we never cite what we don't hold
    code = _resolve(topic)
    framework = kb.get("framework") or kb.get("key_points", [])

    analysis = (
        f"Under {kb['asc']} ({kb['title']}), {kb['summary']} "
        f"Applying this to the facts requires working through: " + "; ".join(framework) + ". "
        "Each element should be evaluated against the specific facts; judgments (e.g. fair value, "
        "variable consideration, classification, useful life) require documented support and may "
        "warrant auditor review."
    )
    alts = alternatives or _ALTERNATIVES.get(code or "", [])
    references = [kb["asc"]] + [f"ASC {c}" for c in _related_codes(code) if c != code]

    return {
        "facts": facts.strip(),
        "issue": issue.strip(),
        "relevant_guidance": {
            "citation": kb["asc"], "title": kb["title"],
            "summary": kb["summary"], "framework": framework,
        },
        "analysis": analysis,
        "alternatives": alts,
        "conclusion": conclusion or (
            f"Account for the matter in accordance with {kb['asc']} and the analysis above. "
            "Confirm the fact pattern and document the judgments; where facts are incomplete the "
            "conclusion is preliminary and should be revisited."
        ),
        "references": references,
        "disclosure_impact": kb.get("disclosures", []),
        "cpa_exam_impact": kb.get("cpa_exam", ""),
        "disclaimer": "Internal research memo. Not a substitute for professional judgment; verify "
                      "against the authoritative Codification.",
    }


def summarize_asu(asu_number: str, title: str, asc_codes: list[str]) -> dict:
    """Summarize an ASU by tying it to known ASC topics it amends."""
    touched = []
    for code in asc_codes:
        if code in ASC_TOPICS:
            kb = ASC_TOPICS[code]
            touched.append({"asc": kb["asc"], "title": kb["title"], "summary": kb["summary"]})
    return {
        "asu": f"ASU {asu_number}" if asu_number else "ASU",
        "title": title,
        "amends": touched,
        "note": ("Amends the topics above — see each for FS impact, disclosures, and CPA relevance."
                 if touched else "References ASC topics outside the current knowledge base; "
                 "fetch the full ASU text for detail."),
    }


def _related_codes(code: Optional[str]) -> list[str]:
    # Lightweight relatedness: revenue↔contract costs, leases↔impairment, etc.
    rel = {"606": ["340"], "842": ["360"], "326": ["310"], "350": ["360"], "718": ["740"]}
    return rel.get(code or "", [])
