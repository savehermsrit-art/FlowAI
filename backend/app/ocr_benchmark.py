"""Small reproducible synthetic OCR benchmark; not a population-level accuracy claim."""

import io
import json
from pathlib import Path

from PIL import Image, ImageFilter
from .documents import process_bytes, synthetic_png, synthetic_pdf


def run(output_dir="data/ocr-fixtures"):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for language in ("en", "kn", "mixed"):
        for quality in ("clear", "blurred"):
            for case in ("A", "C"):
                content = synthetic_png(case, "kn" if language == "kn" else "en")
                if language == "mixed":
                    # Composite actual Kannada and English line regions, not metadata labels.
                    en = Image.open(io.BytesIO(content))
                    kn = Image.open(io.BytesIO(synthetic_png(case, "kn")))
                    en.paste(kn.crop((0, 350, 1800, 500)), (0, 350))
                    buf = io.BytesIO()
                    en.save(buf, format="PNG")
                    content = buf.getvalue()
                if quality == "blurred":
                    image = Image.open(io.BytesIO(content)).filter(ImageFilter.GaussianBlur(4))
                    buf = io.BytesIO()
                    image.save(buf, format="PNG")
                    content = buf.getvalue()
                name = f"{language}-{quality}-{case}"
                (root / (name + ".png")).write_bytes(content)
                expected = {"age": "45" if case == "C" else "70", "state": "Karnataka", "annual_income": "30000"}
                try:
                    facts, meta = process_bytes(content, "image/png")
                    original = {f["key"]: f["original"] for f in facts}
                    normalized = {f["key"]: f["value"] for f in facts}
                    rows.append(
                        {
                            "id": name,
                            "language": language,
                            "quality": quality,
                            "document_type": "synthetic_combined_scan",
                            "expected": expected,
                            "original": original,
                            "normalized": normalized,
                            "exact_matches": sum(original.get(k) == v for k, v in expected.items()),
                            "normalized_matches": sum(normalized.get(k) == v for k, v in expected.items()),
                            "missing_fields": sorted(set(expected) - set(normalized)),
                            "failed": False,
                            "quality_warnings": [w for p in meta["pages"] for w in p["warnings"]],
                        }
                    )
                except Exception as exc:
                    rows.append(
                        {
                            "id": name,
                            "language": language,
                            "quality": quality,
                            "expected": expected,
                            "exact_matches": 0,
                            "normalized_matches": 0,
                            "missing_fields": list(expected),
                            "failed": True,
                            "error": type(exc).__name__,
                        }
                    )
    strata = {}
    for language in ("en", "kn", "mixed"):
        subset = [r for r in rows if r["language"] == language]
        strata[language] = {
            "field_exact_match": sum(r["exact_matches"] for r in subset) / (len(subset) * 3),
            "normalized_accuracy": sum(r["normalized_matches"] for r in subset) / (len(subset) * 3),
            "missing_fields": sum(len(r["missing_fields"]) for r in subset),
            "processing_failures": sum(r["failed"] for r in subset),
        }
    # Document-specific fixtures exercise the text-PDF path separately from image OCR.
    pdfs = []
    for category, key, value in (
        ("age_proof", "age", "70"),
        ("residence", "state", "Karnataka"),
        ("income", "annual_income", "30000"),
    ):
        content = synthetic_pdf("A", category)
        (root / f"en-{category}.pdf").write_bytes(content)
        fs, _ = process_bytes(content, "application/pdf")
        pdfs.append(
            {
                "document_type": category,
                "expected_field": key,
                "exact_match": any(f["key"] == key and f["value"] == value for f in fs),
            }
        )
    result = {
        "scope": "12 synthetic scanned images (English, Kannada, mixed; clear and blurred) plus 3 text PDFs. No real citizen data. Small fixture benchmark only.",
        "image_cases": len(rows),
        "by_language": strata,
        "pdf_by_document_type": pdfs,
        "cases": rows,
    }
    (root.parent / "ocr-evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    run()
