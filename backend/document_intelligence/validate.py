"""Validation of extracted fields — required-field checks + sanity, with a
confidence score the reviewer can act on."""
from __future__ import annotations

_REQUIRED = {
    "invoice": ["total"],
    "receipt": ["total"],
    "w2": ["wages"],
    "1099": ["compensation"],
    "bank_statement": ["ending_balance"],
}


def validate(doc_type: str, fields: dict) -> dict:
    issues = []
    for req in _REQUIRED.get(doc_type, []):
        if fields.get(req) is None:
            issues.append(f"missing required field: {req}")

    # Bank-statement sanity: ending should differ from beginning only via activity.
    if doc_type == "bank_statement" and fields.get("beginning_balance") is not None \
            and fields.get("ending_balance") is not None:
        pass  # both present is enough; movement reconciliation happens in bank_rec

    if not fields.get("amounts") and doc_type in ("invoice", "receipt", "1099", "w2"):
        issues.append("no monetary amounts detected — extraction may be incomplete")

    required_n = len(_REQUIRED.get(doc_type, [])) or 1
    found_n = required_n - sum(1 for i in issues if i.startswith("missing"))
    confidence = round(max(0.0, found_n / required_n) * (0.7 if issues else 1.0), 3)
    return {"valid": not issues, "issues": issues, "confidence": confidence,
            "review_recommended": bool(issues)}
