"""Document intelligence pipeline: extract → classify → extract fields → validate
→ summarize. Returns one structured result linking the document to its data.
"""
from __future__ import annotations

import re

from . import classify, extract, textextract, validate


def _summarize(text: str, max_sentences: int = 3) -> str:
    """Extractive summary: the first substantive sentences (no fabrication)."""
    clean = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    picked = [s for s in sentences if len(s) > 20][:max_sentences]
    return " ".join(picked)[:600]


def _assemble(extracted: dict) -> dict:
    text = extracted.get("text", "")
    cls = classify.classify(text)
    fields = extract.extract_fields(cls["doc_type"], text)
    val = validate.validate(cls["doc_type"], fields)
    return {
        "format": extracted.get("format"),
        "method": extracted.get("method"),
        "filename": extracted.get("filename"),
        "extraction_confidence": extracted.get("confidence"),
        "needs_ocr": extracted.get("needs_ocr", False),
        "doc_type": cls["doc_type"],
        "classification_confidence": cls["confidence"],
        "classification_scores": cls["scores"],
        "fields": fields,
        "validation": val,
        "summary": _summarize(text),
        "text_preview": text[:1000],
        "text_length": len(text),
    }


def process(path: str) -> dict:
    return _assemble(textextract.extract_text(path))


def process_bytes(filename: str, data: bytes) -> dict:
    return _assemble(textextract.process_bytes(filename, data))


def process_text(text: str, filename: str = "inline.txt") -> dict:
    """Classify/extract directly from already-extracted text (used by tests/APIs)."""
    return _assemble({"text": text, "format": "text", "method": "inline",
                      "filename": filename, "confidence": 1.0})
