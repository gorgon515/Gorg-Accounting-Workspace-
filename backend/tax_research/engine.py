"""Tax Research Engine — a citable tax-authority knowledge base, authority
hierarchy, issue analysis, risk assessment, planning, and a tax-memo generator.

Like the accounting research engine, it only cites authorities it actually holds
(real IRC/Reg/Ruling/case citations) and flags where facts or judgment govern.
"""
from __future__ import annotations

from typing import Optional

# Authority weight by type (higher = more authoritative). Drives the hierarchy.
AUTHORITY_WEIGHT = {
    "statute": 100, "regulation": 90, "court_supreme": 88, "court_appeals": 78,
    "revenue_ruling": 72, "revenue_procedure": 72, "court_tax": 66, "notice": 60,
    "announcement": 50, "private_ruling": 30, "publication": 25,
}

# Seeded tax topics with real primary authorities.
TAX_TOPICS: dict[str, dict] = {
    "home_office": {
        "issue": "Deductibility of home office expenses",
        "summary": "A home office is deductible if used regularly and exclusively as the principal "
                   "place of business; a simplified safe-harbor method is available.",
        "authorities": [
            {"cite": "IRC §280A", "type": "statute"},
            {"cite": "Rev. Proc. 2013-13", "type": "revenue_procedure"},
            {"cite": "IRS Pub. 587", "type": "publication"},
        ],
        "planning": ["Use the $5/sq ft safe harbor (max 300 sq ft) to avoid actual-expense recordkeeping.",
                     "Ensure regular AND exclusive business use to preserve the deduction."],
        "risk": "Exclusive-use failures and overstated square footage are common audit triggers.",
        "keywords": ["home office", "280a", "principal place of business", "exclusive use"],
    },
    "business_meals": {
        "issue": "Deductibility of business meals",
        "summary": "Business meals are generally 50% deductible if ordinary, necessary, and not lavish, "
                   "with the taxpayer (or employee) present.",
        "authorities": [
            {"cite": "IRC §274(n)", "type": "statute"},
            {"cite": "Treas. Reg. §1.274-12", "type": "regulation"},
            {"cite": "Notice 2021-25", "type": "notice"},
        ],
        "planning": ["Separate meals from entertainment (entertainment is nondeductible post-TCJA).",
                     "Document business purpose and attendees contemporaneously."],
        "risk": "Entertainment disallowance and inadequate substantiation under §274(d).",
        "keywords": ["meals", "274", "entertainment", "50%"],
    },
    "section_179": {
        "issue": "Expensing of qualifying property under §179",
        "summary": "Taxpayers may elect to expense the cost of qualifying property, subject to annual "
                   "dollar and taxable-income limitations, in lieu of depreciation.",
        "authorities": [
            {"cite": "IRC §179", "type": "statute"},
            {"cite": "Treas. Reg. §1.179-1", "type": "regulation"},
            {"cite": "IRC §168(k)", "type": "statute"},
        ],
        "planning": ["Coordinate §179 with §168(k) bonus depreciation for optimal timing.",
                     "Watch the taxable-income limitation — §179 cannot create a loss."],
        "risk": "Recapture on business-use drops below 50%; income-limitation miscalculation.",
        "keywords": ["179", "bonus depreciation", "168", "expensing", "equipment"],
    },
    "qbi": {
        "issue": "Qualified Business Income deduction (§199A)",
        "summary": "Eligible pass-through owners may deduct up to 20% of qualified business income, "
                   "subject to wage/UBIA limits and SSTB phase-outs above threshold.",
        "authorities": [
            {"cite": "IRC §199A", "type": "statute"},
            {"cite": "Treas. Reg. §1.199A-1", "type": "regulation"},
        ],
        "planning": ["Manage taxable income around the threshold to preserve the deduction for SSTBs.",
                     "Increase W-2 wages or UBIA to relax the limitation above the threshold."],
        "risk": "SSTB classification and the wage/UBIA limitation are judgment-intensive.",
        "keywords": ["qbi", "199a", "pass-through", "sstb", "20% deduction"],
    },
    "s_corp_comp": {
        "issue": "Reasonable compensation for S-corporation shareholder-employees",
        "summary": "S-corp shareholder-employees must take reasonable W-2 compensation for services "
                   "before taking distributions; the IRS can recharacterize distributions as wages.",
        "authorities": [
            {"cite": "IRC §1366", "type": "statute"},
            {"cite": "Rev. Rul. 74-44", "type": "revenue_ruling"},
            {"cite": "Watson v. Commissioner, 668 F.3d 1008 (8th Cir. 2012)", "type": "court_appeals"},
        ],
        "planning": ["Benchmark compensation to comparable roles; document the basis.",
                     "Pay reasonable salary before distributions to mitigate recharacterization."],
        "risk": "Under-compensation is a high-profile audit issue with payroll-tax exposure.",
        "keywords": ["s corp", "reasonable compensation", "1366", "distributions", "shareholder"],
    },
    "hobby_loss": {
        "issue": "Hobby loss limitations (§183)",
        "summary": "Activities not engaged in for profit limit deductions to income; a profit in 3 of 5 "
                   "years creates a presumption of profit motive.",
        "authorities": [
            {"cite": "IRC §183", "type": "statute"},
            {"cite": "Treas. Reg. §1.183-2", "type": "regulation"},
        ],
        "planning": ["Maintain businesslike records and a written profit plan to evidence profit motive.",
                     "Track the 3-of-5-year safe harbor."],
        "risk": "Post-TCJA, hobby expenses are nondeductible while hobby income is taxable.",
        "keywords": ["hobby", "183", "profit motive", "not for profit"],
    },
}

_ALIASES = {"home office": "home_office", "meals": "business_meals", "179": "section_179",
            "qbi": "qbi", "199a": "qbi", "s corp": "s_corp_comp", "reasonable compensation": "s_corp_comp",
            "hobby": "hobby_loss"}


def _resolve(topic: str) -> Optional[str]:
    t = str(topic or "").strip().lower()
    if t in TAX_TOPICS:
        return t
    if t in _ALIASES:
        return _ALIASES[t]
    for key, data in TAX_TOPICS.items():
        if any(kw in t for kw in data["keywords"]):
            return key
    return None


def list_topics() -> list[dict]:
    return [{"key": k, "issue": v["issue"]} for k, v in TAX_TOPICS.items()]


def authority_hierarchy(authorities: list[dict]) -> list[dict]:
    ranked = sorted(authorities, key=lambda a: -AUTHORITY_WEIGHT.get(a["type"], 0))
    return [{**a, "weight": AUTHORITY_WEIGHT.get(a["type"], 0)} for a in ranked]


def research(query: str) -> dict:
    """Return the matched topic with authorities ranked by the hierarchy."""
    key = _resolve(query)
    if not key:
        raise ValueError(f"'{query}' not in the tax knowledge base. Topics: "
                         + ", ".join(TAX_TOPICS))
    t = TAX_TOPICS[key]
    return {"topic": key, "issue": t["issue"], "summary": t["summary"],
            "authorities": authority_hierarchy(t["authorities"]),
            "planning_opportunities": t["planning"], "risk_assessment": t["risk"]}


def generate_memo(facts: str, issues: str, topic: str, *, alternatives: Optional[list[str]] = None,
                  conclusion: Optional[str] = None) -> dict:
    if not facts or not facts.strip():
        raise ValueError("facts are required")
    if not issues or not issues.strip():
        raise ValueError("issues are required")
    r = research(topic)  # raises if unknown — never cite what we don't hold
    cites = [a["cite"] for a in r["authorities"]]
    analysis = (
        f"The governing authority is {cites[0]}. {r['summary']} Applying this to the facts requires "
        f"evaluating the statutory/regulatory tests above; the highest authority controls where sources "
        f"conflict. Areas turning on facts or judgment should be documented with contemporaneous support."
    )
    return {
        "facts": facts.strip(), "issues": issues.strip(),
        "authorities": r["authorities"],
        "analysis": analysis,
        "alternatives": alternatives or ["Apply the safe harbor where available", "Take the position with full disclosure (Form 8275) if support is substantial-authority but not certain"],
        "conclusion": conclusion or (f"Based on {cites[0]} and the analysis, the position is supportable on "
                                     "the stated facts; confirm the facts and substantiation before filing."),
        "recommendations": r["planning_opportunities"],
        "risk_assessment": r["risk_assessment"],
        "references": cites,
        "disclaimer": "Internal tax research memo. Not tax advice for a specific taxpayer without engagement; "
                      "verify against current primary authority (the law changes).",
    }
