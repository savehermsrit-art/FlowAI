from PIL import Image
from app.documents import extract, process_bytes, quality_and_preprocess, synthetic_pdf, classify
from app.monitor import classify_change


def test_extraction_bilingual_and_provenance():
    lines = [
        {"text": "ವಯಸ್ಸು: 70", "page": 2, "bbox": [1, 2, 3, 4], "confidence": 0.93},
        {"text": "ರಾಜ್ಯ: ಕರ್ನಾಟಕ", "page": 2, "bbox": [1, 4, 3, 7], "confidence": 0.96},
        {"text": "Annual income: INR 30,000", "page": 3, "bbox": [1, 2, 3, 4], "confidence": 0.91},
        {"text": "Issued: 2026-11-17", "page": 3, "bbox": [1, 2, 3, 4], "confidence": 0.91},
    ]
    facts = extract(lines, "test")
    assert {f["key"]: f["value"] for f in facts} == {"age": "70", "state": "Karnataka", "annual_income": "30000"}
    assert facts[0]["page"] == 2 and facts[0]["bbox"] == [1, 2, 3, 4]
    assert facts[2]["original"] == "30,000"
    assert classify("ವಾರ್ಷಿಕ ಆದಾಯ") == "income"


def test_pdf_and_quality():
    facts, quality = process_bytes(synthetic_pdf("C", "age_proof"), "application/pdf")
    assert facts[0]["value"] == "45" and facts[0]["method"] == "pdf_text"
    image = Image.new("RGB", (200, 200), "white")
    processed, quality = quality_and_preprocess(image)
    assert "BLURRED" in quality["warnings"] and "LOW_RESOLUTION" in quality["warnings"]


def test_change_classifier():
    assert classify_change("income 50000", "income 51000") == "eligibility"
    assert classify_change("hello world", "hello  world") == "cosmetic"
    assert classify_change("last date 1", "last date 2") == "deadlines"


def test_income_units_decimals_and_page_dates_are_not_guessed():
    def line(text, page=1):
        return {"text": text, "page": page, "bbox": [0, 0, 100, 20], "confidence": 1}

    assert extract([line("Monthly income: INR 5000")], "test") == []
    assert extract([line("Coverage: 70")], "test") == []
    fs = extract(
        [line("Annual income: INR 50,000.50"), line("Issued: 2020-01-01"), line("Issued: 2026-11-17", 2)], "test"
    )
    assert fs[0]["value"] == "50000.50" and fs[0]["issued_at"] == "2020-01-01"
    fs = extract([line("Annual income: INR 30000"), line("Issued: 2020-01-01"), line("Issued: 2026-11-17")], "test")
    assert fs[0]["issued_at"] is None
