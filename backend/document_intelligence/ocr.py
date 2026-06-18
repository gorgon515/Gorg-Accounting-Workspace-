"""OCR backend — real Tesseract image OCR, honestly availability-gated.

If the Tesseract binary is not installed, OCR is reported unavailable and raises
``OCRUnavailable`` — it NEVER fabricates text. With Tesseract present, it returns
the recognized text plus a real mean word-confidence from Tesseract's TSV output.
PaddleOCR can be slotted behind the same interface as an optional backend.
"""
from __future__ import annotations

import shutil
from functools import lru_cache


class OCRUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def tesseract_available() -> bool:
    if not shutil.which("tesseract"):
        return False
    try:
        import pytesseract  # noqa: F401
        return True
    except Exception:
        return False


def engine_status() -> dict:
    return {
        "tesseract": tesseract_available(),
        "binary": shutil.which("tesseract"),
        "note": ("Tesseract available — image OCR enabled." if tesseract_available()
                 else "Tesseract not installed. Install it (e.g. `apt-get install tesseract-ocr`) "
                      "to OCR scanned images. PDF/Excel/Word/email text extraction works without it."),
    }


def ocr_image(path: str) -> dict:
    """Run Tesseract on an image. Raises OCRUnavailable when the binary is absent."""
    if not tesseract_available():
        raise OCRUnavailable(
            "Tesseract OCR is not installed on this machine, so scanned-image text cannot be "
            "extracted here. Install tesseract-ocr to enable it. (Digital PDFs, Excel, Word, and "
            "email are extracted without OCR.)")
    import pytesseract
    from PIL import Image

    img = Image.open(path)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    words, confs = [], []
    for word, conf in zip(data["text"], data["conf"]):
        if word.strip():
            words.append(word)
            try:
                c = float(conf)
                if c >= 0:
                    confs.append(c)
            except (TypeError, ValueError):
                pass
    text = " ".join(words)
    confidence = round((sum(confs) / len(confs)) / 100, 3) if confs else 0.0
    return {"format": "image", "method": "tesseract", "text": text, "confidence": confidence}
