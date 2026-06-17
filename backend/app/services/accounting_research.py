"""Accounting Intelligence Engine — ASC/GAAP knowledge base + memo generator.

A seeded, citable knowledge base for major ASC topics and a technical-memo
generator that produces the standard structure (Issue / Facts / Guidance /
Analysis / Conclusion / Disclosure impact / CPA-exam impact).

Integrity rules, by design:
  • It only cites ASC topics present in the knowledge base — it does not invent
    citations or paragraph numbers it doesn't hold.
  • Where the answer depends on facts or judgment, the memo says so explicitly
    rather than asserting a false certainty.
The base is intentionally small but real; it is the seed the live FASB/SEC/PCAOB
crawlers (Phase 2) populate and extend, keyed by the same ``asc`` codes.
"""
from __future__ import annotations

from typing import Optional

# ---- ASC knowledge base -------------------------------------------------------
ASC_TOPICS: dict[str, dict] = {
    "606": {
        "asc": "ASC 606",
        "title": "Revenue from Contracts with Customers",
        "summary": "Recognize revenue to depict the transfer of promised goods or "
                   "services in an amount reflecting the consideration expected.",
        "framework": [
            "1. Identify the contract with a customer",
            "2. Identify the performance obligations",
            "3. Determine the transaction price",
            "4. Allocate the transaction price to the obligations",
            "5. Recognize revenue as/when obligations are satisfied",
        ],
        "key_points": [
            "Control transfer drives recognition (point-in-time vs. over-time).",
            "Variable consideration is constrained to amounts highly probable not to reverse.",
            "Distinct goods/services are separate performance obligations.",
        ],
        "fs_impact": "Revenue timing/amount; contract assets and contract liabilities "
                     "(deferred revenue) on the balance sheet.",
        "journal_examples": [
            "Dr Cash/AR  Cr Contract liability (on upfront payment before performance)",
            "Dr Contract liability  Cr Revenue (as the obligation is satisfied)",
        ],
        "disclosures": [
            "Disaggregation of revenue", "Contract balances and changes",
            "Remaining performance obligations", "Significant judgments",
        ],
        "cpa_exam": "FAR — heavily tested: the 5-step model, over-time vs point-in-time, "
                    "principal vs agent, and contract liabilities.",
    },
    "842": {
        "asc": "ASC 842",
        "title": "Leases",
        "summary": "Lessees recognize a right-of-use (ROU) asset and a lease liability "
                   "for substantially all leases over 12 months.",
        "key_points": [
            "Classify as finance or operating; both are on-balance-sheet for lessees.",
            "Initial liability = present value of lease payments.",
            "Operating: single straight-line expense; finance: amortization + interest.",
        ],
        "fs_impact": "Adds ROU assets and lease liabilities; affects expense geography "
                     "and key ratios (leverage, EBITDA).",
        "journal_examples": [
            "Dr ROU asset  Cr Lease liability (commencement, at PV of payments)",
            "Dr Lease expense  Cr Cash / Lease liability (subsequent, operating)",
        ],
        "disclosures": ["Lease cost components", "Weighted-average discount rate and term",
                        "Maturity analysis of lease liabilities"],
        "cpa_exam": "FAR — lessee accounting, finance vs operating classification, "
                    "initial measurement at present value.",
    },
    "326": {
        "asc": "ASC 326",
        "title": "Financial Instruments — Credit Losses (CECL)",
        "summary": "Recognize expected credit losses over the life of financial assets "
                   "using a forward-looking current-expected-credit-loss model.",
        "key_points": [
            "Replaces the incurred-loss model; recognizes lifetime expected losses at origination.",
            "Applies to receivables, held-to-maturity debt, and other financial assets at amortized cost.",
            "Uses historical experience adjusted for current conditions and reasonable forecasts.",
        ],
        "fs_impact": "Allowance for credit losses (contra-asset); earlier loss recognition.",
        "journal_examples": ["Dr Credit loss expense  Cr Allowance for credit losses"],
        "disclosures": ["Credit quality indicators", "Roll-forward of the allowance",
                        "Methodology and assumptions"],
        "cpa_exam": "FAR/AUD — CECL concept, allowance estimation, audit of estimates.",
    },
    "350": {
        "asc": "ASC 350",
        "title": "Intangibles — Goodwill and Other",
        "summary": "Goodwill is not amortized (except under the private-company "
                   "alternative) but tested for impairment at least annually.",
        "key_points": [
            "Impairment = carrying amount over fair value of the reporting unit (capped at goodwill).",
            "Optional qualitative ('Step 0') assessment before the quantitative test.",
            "Finite-lived intangibles are amortized over useful life.",
        ],
        "fs_impact": "Goodwill carrying value; impairment losses hit the income statement.",
        "journal_examples": ["Dr Goodwill impairment loss  Cr Goodwill"],
        "disclosures": ["Goodwill by reporting unit", "Impairment losses and the events causing them"],
        "cpa_exam": "FAR — impairment testing, the one-step quantitative test, qualitative assessment.",
    },
    "718": {
        "asc": "ASC 718",
        "title": "Compensation — Stock Compensation",
        "summary": "Recognize compensation cost for share-based payments at grant-date "
                   "fair value over the requisite service period.",
        "key_points": [
            "Equity-classified awards: measure once at grant-date fair value.",
            "Recognize over the vesting period; account for forfeitures (policy election).",
            "Liability-classified awards are remeasured each period.",
        ],
        "fs_impact": "Compensation expense; additional paid-in capital (equity awards).",
        "journal_examples": ["Dr Compensation expense  Cr APIC — stock options (over vesting)"],
        "disclosures": ["Award terms", "Valuation assumptions", "Unrecognized compensation cost"],
        "cpa_exam": "FAR/REG — grant-date fair value, vesting, and the book-tax difference on options.",
    },
}

# Friendly aliases so callers can pass a topic name instead of a number.
_ALIASES = {
    "revenue": "606", "revenue recognition": "606", "asc 606": "606",
    "leases": "842", "lease": "842", "asc 842": "842",
    "cecl": "326", "credit losses": "326", "asc 326": "326",
    "goodwill": "350", "impairment": "350", "intangibles": "350", "asc 350": "350",
    "stock compensation": "718", "stock comp": "718", "share-based": "718", "asc 718": "718",
}


def _resolve(topic: str) -> Optional[str]:
    t = str(topic or "").strip().lower()
    digits = "".join(ch for ch in t if ch.isdigit())
    if digits in ASC_TOPICS:
        return digits
    return _ALIASES.get(t)


def list_topics() -> list[dict]:
    return [{"asc": v["asc"], "title": v["title"]} for v in ASC_TOPICS.values()]


def explain_asc(topic: str) -> dict:
    """Return the structured knowledge-base entry for an ASC topic."""
    key = _resolve(topic)
    if not key:
        raise ValueError(
            f"'{topic}' not in the knowledge base. Available: "
            + ", ".join(v["asc"] for v in ASC_TOPICS.values())
        )
    return ASC_TOPICS[key]


def generate_memo(issue: str, facts: str, topic: str, conclusion: Optional[str] = None) -> dict:
    """Generate a technical accounting memo in the standard structure.

    ``topic`` is grounded in the knowledge base; guidance/disclosure/CPA sections
    are drawn from the cited ASC. The analysis ties the user's ``facts`` to that
    guidance and flags where professional judgment is required.
    """
    if not issue or not str(issue).strip():
        raise ValueError("issue is required")
    if not facts or not str(facts).strip():
        raise ValueError("facts are required")
    kb = explain_asc(topic)  # raises if unknown — we never cite what we don't hold

    framework = kb.get("framework") or kb.get("key_points", [])
    analysis = (
        f"Applying {kb['asc']} ({kb['title']}) to the stated facts: "
        f"{kb['summary']} The relevant considerations are — "
        + "; ".join(framework)
        + ". The facts should be evaluated against each; areas involving estimates or "
        "judgment (e.g. fair value, variable consideration, useful life, classification) "
        "require management's documented support and may warrant auditor review."
    )
    derived_conclusion = conclusion or (
        f"Based on {kb['asc']} and the facts presented, account for the matter consistent "
        f"with the guidance above. Confirm the fact pattern and judgments with supporting "
        f"documentation before finalizing; where facts are incomplete, the conclusion is "
        f"preliminary."
    )
    return {
        "issue": str(issue).strip(),
        "facts": str(facts).strip(),
        "guidance": {
            "citation": kb["asc"],
            "title": kb["title"],
            "summary": kb["summary"],
            "framework": framework,
        },
        "analysis": analysis,
        "conclusion": derived_conclusion,
        "disclosure_impact": kb.get("disclosures", []),
        "cpa_exam_impact": kb.get("cpa_exam", ""),
        "citations": [kb["asc"]],
        "disclaimer": "Generated research memo for internal use. Not a substitute for "
                      "professional judgment; verify against the authoritative standard.",
    }
