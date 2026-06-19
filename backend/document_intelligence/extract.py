"""Structured field extraction from document text (regex over real OCR/text)."""
from __future__ import annotations

import re

# Either a comma-grouped number (1,234.56) or a full run (85000.00 / 1234 / 1234.56).
_NUM = r"(-?\d{1,3}(?:,\d{3})+(?:\.\d{2})?|-?\d+(?:\.\d{2})?)"
_MONEY = re.compile(r"\$?\s?" + _NUM)
_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|"
                   r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b", re.I)


def _money(s: str):
    try:
        return float(s.replace(",", "").replace("$", "").strip())
    except (ValueError, AttributeError):
        return None


def _all_money(text: str) -> list[float]:
    out = []
    for m in _MONEY.finditer(text):
        v = _money(m.group(1))
        if v is not None:
            out.append(v)
    return out


def _labeled(text: str, label_pattern: str):
    # Allow non-digit characters (words, colons, $) between the label and the
    # value on the same line, e.g. "Box 1 Wages, tips ...: 85000.00".
    m = re.search(label_pattern + r"[^0-9\n]*?" + _NUM, text, re.I)
    return _money(m.group(1)) if m else None


def _dates(text: str) -> list[str]:
    return [m.group(1) for m in _DATE.finditer(text)][:10]


def extract_fields(doc_type: str, text: str) -> dict:
    f: dict = {"amounts": _all_money(text)[:20], "dates": _dates(text)}

    if doc_type == "invoice":
        num = re.search(r"invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)", text, re.I)
        f["invoice_number"] = num.group(1) if num else None
        f["total"] = _labeled(text, r"(?:total|amount due|balance due|grand total)")

    elif doc_type == "receipt":
        f["total"] = _labeled(text, r"(?:total|amount)")
        f["subtotal"] = _labeled(text, r"subtotal")

    elif doc_type == "w2":
        f["wages"] = _labeled(text, r"(?:box 1|wages,? tips)")
        f["federal_tax_withheld"] = _labeled(text, r"(?:box 2|federal income tax withheld)")
        f["social_security_wages"] = _labeled(text, r"social security wages")
        emp = re.search(r"employer[:\s]+([A-Za-z0-9 ,.&'-]{3,60})", text, re.I)
        f["employer"] = emp.group(1).strip() if emp else None

    elif doc_type == "1099":
        f["compensation"] = _labeled(text, r"(?:nonemployee compensation|box 1)")
        payer = re.search(r"payer'?s?\s*name[:\s]+([A-Za-z0-9 ,.&'-]{3,60})", text, re.I)
        f["payer"] = payer.group(1).strip() if payer else None

    elif doc_type == "bank_statement":
        f["beginning_balance"] = _labeled(text, r"beginning balance")
        f["ending_balance"] = _labeled(text, r"ending balance")
        period = re.search(r"statement period[:\s]+(.{5,40})", text, re.I)
        f["period"] = period.group(1).strip() if period else None

    elif doc_type == "k1":
        f["ordinary_income"] = _labeled(text, r"ordinary business income")

    # A best-guess primary amount for any document with money.
    if f.get("total") is None and f["amounts"]:
        f["max_amount"] = max(f["amounts"])
    return f
