"""Reproducible, bounded official-source collection. Run with Python 3.11+.

The curated manifest is the crawl boundary. This never follows arbitrary links or
interprets a fetched page as instructions. Failed fetches remain in the manifest.
"""

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1] / "data" / "research"
HOSTS = {"chitradurga.nic.in", "vijayapura.nic.in", "dssp.karnataka.gov.in"}


class MainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.main = 0
        self.skip = 0
        self.section = "page"
        self.tag = ""
        self.parts = []
        self.lines = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "main" or attrs.get("id") == "main-content":
            self.main += 1
        if self.main and tag in ("script", "style", "nav"):
            self.skip += 1
        if self.main and tag in ("h1", "h2", "h3", "h4", "p", "li", "td", "th"):
            self.flush()
            self.tag = tag

    def handle_endtag(self, tag):
        if self.main and tag in ("h1", "h2", "h3", "h4", "p", "li", "td", "th"):
            self.flush()
        if self.main and tag in ("script", "style", "nav") and self.skip:
            self.skip -= 1
        if tag == "main" and self.main:
            self.main -= 1

    def handle_data(self, data):
        if self.main and not self.skip:
            self.parts.append(data)

    def flush(self):
        line = " ".join("".join(self.parts).split())
        self.parts = []
        if line:
            if self.tag in ("h1", "h2", "h3", "h4"):
                self.section = line
            self.lines.append({"section": self.section, "text": line})


def extract_html(raw):
    parser = MainText()
    parser.feed(raw.decode("utf-8", errors="replace"))
    parser.flush()
    return parser.lines


def extract_pdf(raw):
    try:
        import pymupdf
    except ImportError:
        return [], "PyMuPDF not installed; original PDF retained"
    document = pymupdf.open(stream=raw, filetype="pdf")
    lines = []
    for page_no, page in enumerate(document, 1):
        for line in page.get_text().splitlines():
            line = " ".join(line.split())
            if line:
                lines.append({"section": f"page {page_no}", "page": page_no, "text": line})
    full_text = " ".join(line["text"] for line in lines)
    kannada_letters = sum("\u0c80" <= char <= "\u0cff" for char in full_text)
    if full_text and kannada_letters / len(full_text) < 0.02:
        return [], "Embedded text is not usable Kannada; PDF retained for independent OCR and review"
    return lines, None if lines else "PDF has no embedded text; OCR review required"


def fetch(item, timeout=25):
    parsed = urlparse(item["url"])
    if parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.username or parsed.port not in (None, 443):
        raise ValueError("source URL is not on the HTTPS allowlist")
    # macOS's system curl uses the host trust store when a local Python install
    # lacks CA certificates. Redirects are intentionally disabled.
    with tempfile.TemporaryDirectory() as temporary:
        destination = Path(temporary) / "response"
        result = subprocess.run(
            ["curl", "--fail", "--silent", "--show-error", "--max-time", str(timeout),
             "--proto", "=https", "--max-filesize", "8000000", "--user-agent",
             "FormFlowResearch/1.0 (bounded public-source archive)", "--output", str(destination),
             "--write-out", "%{http_code}", item["url"]],
            capture_output=True, timeout=timeout + 2, check=False,
        )
        if result.returncode:
            raise ValueError(f"curl exit {result.returncode}: {result.stderr.decode(errors='replace')[:200]}")
        if result.stdout.decode().strip() != "200":
            raise ValueError(f"Unexpected HTTP status {result.stdout.decode().strip()}; redirects are not followed")
        content = destination.read_bytes()
        if len(content) > 8_000_000:
            raise ValueError("source exceeds 8 MB limit")
        if item["type"] == "pdf" and not content.startswith(b"%PDF"):
            raise ValueError("Expected PDF signature")
        return content, "application/pdf" if item["type"] == "pdf" else "text/html"


def ingest(root=ROOT, delay=0.5):
    root.mkdir(parents=True, exist_ok=True)
    raw_dir = root / "raw"
    raw_dir.mkdir(exist_ok=True)
    version_dir = root / "versions"
    version_dir.mkdir(exist_ok=True)
    items = json.loads((root / "sources.json").read_text())
    records = []
    passages = []
    for item in items:
        record = dict(item)
        record["retrieved_at"] = datetime.now(UTC).isoformat()
        record["source_version"] = None
        record["content_hash"] = None
        record["publication_date"] = item.get("publication_date")
        record["effective_date"] = None
        try:
            raw, content_type = fetch(item)
            digest = hashlib.sha256(raw).hexdigest()
            extension = ".pdf" if item["type"] == "pdf" else ".html"
            path = raw_dir / f"{digest}{extension}"
            path.write_bytes(raw)
            record.update(content_hash=digest, source_version=digest[:12], raw_path=str(path.relative_to(root)), content_type=content_type, status="fetched")
            if item["type"] == "pdf":
                lines, note = extract_pdf(raw)
                if note:
                    record["extraction_note"] = note
            else:
                lines = extract_html(raw)
                updated = re.search(r"Last Updated(?: On)?:?\s*(\d{2}[.-]\d{2}[.-]\d{4})", raw.decode("utf-8", errors="replace"), re.IGNORECASE)
                if updated:
                    record["site_last_updated"] = updated.group(1)
            for index, line in enumerate(lines):
                if len(line["text"]) < 8:
                    continue
                passage = {"id": f"{item['id']}:{digest[:12]}:{index}", "source_id": item["id"], "scheme_id": item["scheme_id"], "department": item["department"], "language": item["language"], "version": digest[:12], "section": line["section"], "page": line.get("page"), "text": line["text"], "url": item["url"]}
                passages.append(passage)
            record["passage_count"] = len(lines)
            version_path = version_dir / item["id"]
            version_path.mkdir(exist_ok=True)
            (version_path / f"{digest}.json").write_text(json.dumps({"source": record, "passages": [p for p in passages if p["source_id"] == item["id"]]}, ensure_ascii=False, indent=2) + "\n")
        except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
            record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        records.append(record)
        time.sleep(delay)
    (root / "manifest.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
    (root / "passages.json").write_text(json.dumps(passages, ensure_ascii=False, indent=2) + "\n")
    with (root / "attempts.jsonl").open("a") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return records, passages


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()
    records, passages = ingest(delay=args.delay)
    print(json.dumps({"fetched": sum(r["status"] == "fetched" for r in records), "failed": [r["id"] for r in records if r["status"] == "failed"], "passages": len(passages)}))
