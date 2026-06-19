"""Document classification — transparent keyword/pattern scoring with confidence.

Rules-based and explainable (no opaque model): each document type has weighted
signals; the winner's confidence is its share of total matched weight.
"""
from __future__ import annotations

import re

# doc_type → list of (regex, weight)
_SIGNALS: dict[str, list[tuple[str, float]]] = {
    "w2": [(r"\bW-?2\b", 3), (r"wage and tax statement", 4), (r"\bbox 1\b", 1.5),
           (r"social security wages", 2), (r"employer identification", 1)],
    "1099": [(r"\b1099(-(NEC|MISC|INT|DIV|K|B|R))?\b", 3), (r"nonemployee compensation", 3),
             (r"payer'?s? (name|tin)", 1.5)],
    "k1": [(r"schedule k-?1", 4), (r"partner'?s? share", 3), (r"beneficiary'?s? share", 3),
           (r"\b1065\b|\b1120-?S\b", 1.5)],
    "invoice": [(r"\binvoice\b", 3), (r"invoice (no|number|#)", 3), (r"bill to", 2),
                (r"amount due", 2), (r"\bpurchase order\b|\bP\.?O\.?\b", 1)],
    "receipt": [(r"\breceipt\b", 3), (r"subtotal", 2), (r"\bchange due\b", 2),
                (r"thank you for your (purchase|business)", 2), (r"\bcash\b|\bvisa\b|\bmastercard\b", 1)],
    "bank_statement": [(r"statement period", 3), (r"beginning balance", 3), (r"ending balance", 3),
                       (r"account (number|summary)", 2), (r"deposits and credits", 2)],
    "contract": [(r"\bagreement\b", 2.5), (r"\bhereby\b", 2), (r"terms and conditions", 2),
                 (r"\bparty\b|\bparties\b", 1.5), (r"in witness whereof", 3)],
    "tax_return": [(r"form 1040", 4), (r"adjusted gross income", 3), (r"taxable income", 2),
                   (r"\brefund\b|\bamount you owe\b", 1.5)],
    "financial_statement": [(r"balance sheet", 3), (r"income statement", 3), (r"statement of cash flows", 3),
                            (r"total assets", 2), (r"net income", 1.5), (r"retained earnings", 1.5)],
    "research_memo": [(r"memorandum", 3), (r"\bfacts\b", 1.5), (r"\bissue[s]?\b", 1.5),
                      (r"\banalysis\b", 1.5), (r"\bconclusion\b", 1.5)],
    "audit_workpaper": [(r"workpaper|work paper", 4), (r"tickmark", 3), (r"prepared by", 2),
                        (r"reviewed by", 2), (r"lead schedule", 3)],
    "client_correspondence": [(r"^dear\b", 2), (r"\b(regards|sincerely|best regards)\b", 2),
                              (r"following up", 1.5), (r"please find attached", 1.5)],
}

_COMPILED = {dt: [(re.compile(p, re.I | re.M), w) for p, w in sigs] for dt, sigs in _SIGNALS.items()}


def classify(text: str) -> dict:
    if not text or not text.strip():
        return {"doc_type": "unknown", "confidence": 0.0, "scores": {}}
    scores: dict[str, float] = {}
    for dt, sigs in _COMPILED.items():
        s = sum(w for pat, w in sigs if pat.search(text))
        if s > 0:
            scores[dt] = round(s, 2)
    if not scores:
        return {"doc_type": "unknown", "confidence": 0.0, "scores": {}}
    total = sum(scores.values())
    top = max(scores, key=scores.get)
    return {"doc_type": top, "confidence": round(scores[top] / total, 3),
            "scores": dict(sorted(scores.items(), key=lambda kv: -kv[1]))}
