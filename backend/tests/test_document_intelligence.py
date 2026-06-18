import os
import tempfile
import unittest

from document_intelligence import classify, extract, validate, pipeline, ocr
from document_intelligence.store import DocStore

W2_TEXT = ("Form W-2 Wage and Tax Statement 2024\nEmployer: Globex Corporation\n"
           "Box 1 Wages, tips, other compensation: 85000.00\n"
           "Box 2 Federal income tax withheld: 12500.00\nSocial security wages: 85000.00")
INV_TEXT = ("INVOICE\nInvoice Number: INV-1001\nBill To: Acme Corp\n"
            "Date: 2025-03-15\nTotal Amount Due: $1,234.56")


def _make_invoice_pdf() -> str:
    from reportlab.pdfgen import canvas
    path = os.path.join(tempfile.mkdtemp(), "invoice.pdf")
    c = canvas.Canvas(path)
    y = 800
    for line in INV_TEXT.split("\n"):
        c.drawString(72, y, line)
        y -= 20
    c.save()
    return path


class TextExtractionTest(unittest.TestCase):
    def test_real_pdf_text_layer(self):
        result = pipeline.process(_make_invoice_pdf())
        # Real extraction from a real PDF — not OCR, not fabricated.
        self.assertEqual(result["format"], "pdf")
        self.assertEqual(result["extraction_confidence"], 1.0)
        self.assertIn("INV-1001", result["text_preview"])
        self.assertEqual(result["doc_type"], "invoice")
        self.assertEqual(result["fields"]["invoice_number"], "INV-1001")
        self.assertAlmostEqual(result["fields"]["total"], 1234.56)


class ClassifyTest(unittest.TestCase):
    def test_w2_and_1099_and_invoice(self):
        self.assertEqual(classify.classify(W2_TEXT)["doc_type"], "w2")
        self.assertEqual(classify.classify("Form 1099-NEC Nonemployee compensation: 5000")["doc_type"], "1099")
        self.assertEqual(classify.classify(INV_TEXT)["doc_type"], "invoice")
        self.assertEqual(classify.classify("")["doc_type"], "unknown")

    def test_confidence(self):
        c = classify.classify(W2_TEXT)
        self.assertTrue(0 < c["confidence"] <= 1)


class ExtractValidateTest(unittest.TestCase):
    def test_w2_fields(self):
        f = extract.extract_fields("w2", W2_TEXT)
        self.assertAlmostEqual(f["wages"], 85000.0)
        self.assertAlmostEqual(f["federal_tax_withheld"], 12500.0)

    def test_validation(self):
        ok = validate.validate("invoice", {"total": 100, "amounts": [100]})
        self.assertTrue(ok["valid"])
        bad = validate.validate("invoice", {"amounts": []})
        self.assertFalse(bad["valid"])
        self.assertTrue(bad["issues"])


class OCRTest(unittest.TestCase):
    def test_ocr_is_honestly_gated(self):
        # Tesseract isn't installed here; OCR must report unavailable and NOT fake text.
        status = ocr.engine_status()
        self.assertIn("tesseract", status)
        if not status["tesseract"]:
            with self.assertRaises(ocr.OCRUnavailable):
                ocr.ocr_image("/nonexistent/scan.png")


class StoreTest(unittest.TestCase):
    def test_save_and_search(self):
        store = DocStore(":memory:")
        result = pipeline.process_text(INV_TEXT, "invoice.txt")
        saved = store.save(result, client_id=7)
        self.assertEqual(saved["doc_type"], "invoice")
        self.assertEqual(len(store.search("INV-1001")), 1)
        self.assertEqual(store.search("", doc_type="invoice")[0]["client_id"], 7)
        store.close()


if __name__ == "__main__":
    unittest.main()
