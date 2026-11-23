import io
import re
from datetime import date
from typing import Protocol

import cv2
import pymupdf as fitz
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont

MAX_BYTES = 12 * 1024 * 1024
MAX_PAGES = 10
Image.MAX_IMAGE_PIXELS = 25_000_000


def inspect(content: bytes):
    if not content or len(content) > MAX_BYTES:
        raise ValueError("File must be between 1 byte and 12 MB")
    if content.startswith(b"%PDF-"):
        try:
            with fitz.open(stream=content, filetype="pdf") as doc:
                if doc.is_encrypted or not 1 <= len(doc) <= MAX_PAGES:
                    raise ValueError("Encrypted PDFs or PDFs over 10 pages are unsupported")
                if any(p.rect.width * p.rect.height * 4 > 25_000_000 for p in doc):
                    raise ValueError("PDF page exceeds the safe rendering size")
                for xref in range(1, doc.xref_length()):
                    obj = doc.xref_object(xref)
                    if any(marker in obj for marker in ("/JavaScript", "/Launch", "/EmbeddedFile", "/RichMedia")):
                        raise ValueError("Active PDF content is not accepted")
            return "application/pdf"
        except Exception as exc:
            raise ValueError("Invalid or unsafe PDF") from exc
    try:
        with Image.open(io.BytesIO(content)) as img:
            if img.format not in ("JPEG", "PNG") or img.width * img.height > 25_000_000:
                raise ValueError("Only JPEG and PNG images up to 25 megapixels are accepted")
            fmt = img.format
            img.verify()
        return "image/png" if fmt == "PNG" else "image/jpeg"
    except Exception as exc:
        raise ValueError("File content must be a valid PDF, JPEG or PNG") from exc


class OcrEngine(Protocol):
    def read(self, image: Image.Image, page: int) -> list[dict]: ...


class TesseractEngine:
    def read(self, image, page):
        languages = pytesseract.get_languages(config="")
        if "eng" not in languages or "kan" not in languages:
            raise RuntimeError("Tesseract English and Kannada models are required")
        data = pytesseract.image_to_data(
            image, lang="eng+kan", config="--psm 6", output_type=pytesseract.Output.DICT, timeout=60
        )
        return [
            {
                "text": data["text"][i],
                "confidence": max(0, float(data["conf"][i])) / 100,
                "bbox": [data["left"][i], data["top"][i], data["width"][i], data["height"][i]],
                "page": page,
                "language": "eng+kan",
                "line": (data["block_num"][i], data["par_num"][i], data["line_num"][i]),
            }
            for i in range(len(data["text"]))
            if data["text"][i].strip()
        ]


def quality_and_preprocess(image):
    gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    warnings = []
    if blur < 45:
        warnings.append("BLURRED")
    if min(gray.shape) < 500:
        warnings.append("LOW_RESOLUTION")
    if brightness < 50 or brightness > 253:
        warnings.append("POOR_LIGHTING")
    # Robust skew estimate from foreground coordinates; do not rotate uncertain estimates.
    points = np.column_stack(np.where(gray < 160))
    angle = 0.0
    if len(points) > 50:
        raw = cv2.minAreaRect(points[:, ::-1].astype(np.float32))[-1]
        angle = raw - 90 if raw > 45 else raw
        if 0.5 < abs(angle) < 12:
            matrix = cv2.getRotationMatrix2D((gray.shape[1] / 2, gray.shape[0] / 2), angle, 1)
            gray = cv2.warpAffine(gray, matrix, (gray.shape[1], gray.shape[0]), borderValue=255)
    processed = cv2.fastNlMeansDenoising(gray, h=8)
    processed = cv2.createCLAHE(clipLimit=2, tileGridSize=(8, 8)).apply(processed)
    return Image.fromarray(processed), {
        "blur_score": round(blur, 2),
        "brightness": round(brightness, 2),
        "skew_degrees": round(angle, 2),
        "width": image.width,
        "height": image.height,
        "warnings": warnings,
        "crop_detection": "not verified",
        "rotation": "limited deskew only",
    }


PATTERNS = {
    "dob": r"(?:date of birth|dob|ಜನ್ಮ ದಿನಾಂಕ|ಜನ್ಮದಿನಾಂಕ)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})",
    "age": r"(?:age|ವಯಸ್ಸು)\s*[:\-]?\s*(\d{1,3})",
    "annual_income": r"(?:annual income|ವಾರ್ಷಿಕ ಆದಾಯ)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)",
    "state": r"(?:state|residence|ರಾಜ್ಯ|ವಾಸಸ್ಥಳ)\s*[:\-]?\s*(Karnataka|ಕರ್ನಾಟಕ|Kerala|Tamil Nadu|Maharashtra)",
    "district": r"(?:district|ಜಿಲ್ಲೆ)\s*[:\-]?\s*([A-Za-z\u0c80-\u0cff ]+)",
    "disability_percentage": r"(?:disability|ಅಂಗವೈಕಲ್ಯ)\s*[:\-]?\s*(\d{1,3})\s*%",
    "bpl": r"(?:bpl|ಬಿಪಿಎಲ್)\s*[:\-]?\s*(yes|no|true|false|ಹೌದು|ಇಲ್ಲ)",
    "existing_pension": r"(?:existing pension|ಪಿಂಚಣಿ)\s*[:\-]?\s*(yes|no|true|false|ಹೌದು|ಇಲ್ಲ)",
}


def extract(lines, method):
    facts = []
    # Extract line by line to preserve page, bounding boxes and line-specific confidence.
    issued_by_page = {}
    expires_by_page = {}
    for line in lines:
        m = re.search(r"(?:issued|issue date|ವಿತರಿಸಿದ ದಿನಾಂಕ)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})", line["text"], re.I)
        if m:
            try:
                issued_by_page.setdefault(line["page"], set()).add(date.fromisoformat(m[1]).isoformat())
            except ValueError:
                pass
        m = re.search(r"(?:expires|expiry)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})", line["text"], re.I)
        if m:
            expires_by_page.setdefault(line["page"], set()).add(m[1])
    for line in lines:
        dates = issued_by_page.get(line["page"], set())
        issued = next(iter(dates)) if len(dates) == 1 else None
        expiries = expires_by_page.get(line["page"], set())
        expires = min(expiries) if expiries else None
        for key, pattern in PATTERNS.items():
            match = re.search(r"(?<!\w)" + pattern, line["text"], re.I)
            if not match:
                continue
            original = match[1]
            value = "Karnataka" if original == "ಕರ್ನಾಟಕ" else original.replace(",", "")
            facts.append(
                {
                    "key": key,
                    "original": original,
                    "value": value,
                    "confidence": line["confidence"],
                    "page": line["page"],
                    "bbox": line["bbox"],
                    "method": method,
                    "issued_at": issued,
                    "expires_at": expires,
                }
            )
    return facts


def classify(text):
    t = text.lower()
    if any(s in t for s in ("income", "ಆದಾಯ")):
        return "income"
    if any(s in t for s in ("birth", "age:", "ವಯಸ್ಸು", "ಜನ್ಮ")):
        return "age_proof"
    if any(s in t for s in ("residence", "state:", "ರಾಜ್ಯ")):
        return "residence"
    if "disability" in t:
        return "disability"
    if "pension" in t:
        return "pension"
    if "identity" in t:
        return "identity"
    return "other"


def process_bytes(content, content_type, ocr=None):
    lines, qualities = [], []
    method = "pdf_text"
    pages = []
    page_count = 1
    if content_type == "application/pdf":
        with fitz.open(stream=content, filetype="pdf") as pdf:
            page_count = len(pdf)
            for n, page in enumerate(pdf):
                blocks = page.get_text("dict")["blocks"]
                page_lines = []
                for block in blocks:
                    for line in block.get("lines", []):
                        text = " ".join(span["text"] for span in line["spans"])
                        if text.strip():
                            page_lines.append(
                                {"text": text, "bbox": list(line["bbox"]), "confidence": 1.0, "page": n + 1}
                            )
                if page_lines:
                    lines.extend(page_lines)
                else:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    if pix.width * pix.height > 25_000_000:
                        raise ValueError("PDF page exceeds safe raster size")
                    pages.append((n + 1, Image.frombytes("RGB", [pix.width, pix.height], pix.samples)))
    else:
        pages.append((1, Image.open(io.BytesIO(content)).convert("RGB")))
    for n, image in pages:
        processed, quality = quality_and_preprocess(image)
        qualities.append(quality)
        words = (ocr or TesseractEngine()).read(processed, n)
        groups = {}
        for word in words:
            groups.setdefault(word["line"], []).append(word)
        for group in groups.values():
            left = min(w["bbox"][0] for w in group)
            top = min(w["bbox"][1] for w in group)
            right = max(w["bbox"][0] + w["bbox"][2] for w in group)
            bottom = max(w["bbox"][1] + w["bbox"][3] for w in group)
            lines.append(
                {
                    "text": " ".join(w["text"] for w in group),
                    "confidence": sum(w["confidence"] for w in group) / len(group),
                    "bbox": [left, top, right, bottom],
                    "page": n,
                }
            )
        method = "tesseract_eng_kan"
    text = "\n".join(line["text"] for line in lines)
    return extract(lines, method), {
        "page_count": page_count,
        "pages": qualities,
        "classification": classify(text),
        "ocr_languages": "eng+kan" if pages else "embedded text",
        "text_stored": False,
    }


def synthetic_pdf(case: str, category: str):
    """Public fictional fixtures contain no citizen data."""
    doc = fitz.open()
    page = doc.new_page()
    age = "45" if case == "C" else "70"
    payload = {"age_proof": f"Age: {age}", "residence": "State: Karnataka", "income": "Annual income: INR 30000"}[
        category
    ]
    lines = [
        "FORMFLOW AI - FICTIONAL TEST DOCUMENT",
        "Not a government certificate. No real personal data.",
        f"Synthetic profile {case}",
        payload,
        f"Issued: {date.today().isoformat()}",
    ]
    for i, text in enumerate(lines):
        page.insert_text((60, 80 + i * 35), text, fontsize=14)
    content = doc.tobytes()
    doc.close()
    return content


def synthetic_png(case="A", language="en"):
    image = Image.new("RGB", (1800, 1200), "white")
    draw = ImageDraw.Draw(image)
    import os

    paths = (
        ["/usr/share/fonts/truetype/noto/NotoSansKannada-Regular.ttf", "C:/Windows/Fonts/nirmala.ttf"]
        if language == "kn"
        else ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"]
    )
    font = next((ImageFont.truetype(p, 44) for p in paths if os.path.exists(p)), ImageFont.load_default(size=44))
    age = 45 if case == "C" else 70
    lines = [
        "FICTIONAL TEST - NO REAL PERSONAL DATA",
        f"Age: {age}",
        "State: Karnataka",
        "Annual income: INR 30000",
        f"Issued: {date.today().isoformat()}",
    ]
    if language == "kn":
        lines = [
            "ಕಾಲ್ಪನಿಕ ಪರೀಕ್ಷಾ ದಾಖಲೆ",
            f"ವಯಸ್ಸು: {age}",
            "ರಾಜ್ಯ: ಕರ್ನಾಟಕ",
            "ವಾರ್ಷಿಕ ಆದಾಯ: 30000",
            f"ವಿತರಿಸಿದ ದಿನಾಂಕ: {date.today().isoformat()}",
        ]
    for i, text in enumerate(lines):
        draw.text((90, 90 + i * 150), text, font=font, fill="#111111")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
