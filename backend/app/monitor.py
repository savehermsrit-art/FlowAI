"""Allowlisted official-source fetches; redirects and private-network targets forbidden."""

import difflib
import hashlib
import re
from copy import deepcopy
from datetime import date
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from .db import DB, Source, Snapshot, Scheme, RuleVersion, Proposal

ALLOWED = {"vijayapura.nic.in", "chitradurga.nic.in"}


def classify_change(old, new):
    if " ".join(old.split()) == " ".join(new.split()):
        return "cosmetic"
    changed = " ".join(
        line for line in difflib.ndiff(old.splitlines(), new.splitlines()) if line.startswith(("+ ", "- "))
    ).lower()
    for category, words in [
        ("eligibility", ("age", "income", "resident", "eligible")),
        ("benefit_amount", ("amount", "rupees")),
        ("required_documents", ("certificate", "document")),
        ("deadlines", ("deadline", "last date")),
        ("application_procedures", ("apply", "portal")),
    ]:
        if any(w in changed for w in words):
            return category
    return "administrative"


def ingest_snapshot(db, source, text):
    from .retrieval import index_source

    previous = db.scalar(select(Snapshot).where(Snapshot.source_id == source.id).order_by(Snapshot.created_at.desc()))
    digest = hashlib.sha256(text.encode()).hexdigest()
    if previous and digest == previous.content_hash:
        return None
    db.add(Snapshot(source_id=source.id, content_hash=digest, text=text))
    index_source(db, source, text)
    proposal = None
    if previous:
        scheme = db.get(Scheme, source.scheme_id)
        active = db.get(RuleVersion, f"{scheme.id}:{scheme.active_version}") if scheme.active_version else None
        proposal = Proposal(
            scheme_id=scheme.id,
            base_version=scheme.active_version or 0,
            old_text=previous.text,
            new_text=text,
            classification=classify_change(previous.text, text),
            proposed_rule=deepcopy(active.rule) if active else {},
            regression_cases=[],
        )
        db.add(proposal)
    source.last_error = None
    db.flush()
    return proposal


def monitor_all():
    count = 0
    with DB() as db:
        for source in db.scalars(select(Source)):
            if source.url.startswith("fixture://"):
                continue
            parsed = urlparse(source.url)
            if (
                parsed.scheme != "https"
                or parsed.hostname not in ALLOWED
                or parsed.port not in (None, 443)
                or parsed.username
            ):
                source.last_error = "SOURCE_NOT_ALLOWLISTED"
                continue
            try:
                # No redirects prevents an allowlisted host redirecting to an internal service.
                with httpx.Client(timeout=20, follow_redirects=False) as client:
                    with client.stream(
                        "GET", source.url, headers={"User-Agent": "FormFlowLocalResearch/1.0"}
                    ) as response:
                        response.raise_for_status()
                        content = bytearray()
                        for chunk in response.iter_bytes():
                            content.extend(chunk)
                            if len(content) > 3_000_000:
                                raise ValueError("SOURCE_TOO_LARGE")
                text = content.decode("utf-8", errors="replace")
                text = re.sub(r"(?s)<(script|style).*?</\1>", "", text)
                text = re.sub(r"(?i)</(?:p|div|h[1-6]|li|tr|section)>", "\n\n", text)
                text = re.sub(r"<[^>]+>", " ", text)
                text = "\n\n".join(" ".join(p.split()) for p in text.split("\n\n") if p.strip())
                # Public source bytes are kept locally alongside their normalized database snapshot.
                from .storage import ROOT

                raw_dir = ROOT / "official-sources"
                raw_dir.mkdir(exist_ok=True)
                (raw_dir / (hashlib.sha256(content).hexdigest() + ".html")).write_bytes(content)
                if ingest_snapshot(db, source, text):
                    count += 1
            except Exception as exc:
                source.last_error = type(exc).__name__
        db.commit()
    return count


def simulate_change(db):
    from .evaluation import publication_cases

    source = db.get(Source, "demo-silver")
    scheme = db.get(Scheme, source.scheme_id)
    rule = deepcopy(db.get(RuleVersion, f"{scheme.id}:{scheme.active_version}").rule)
    threshold = next(c["value"] for c in rule["conditions"] if c["id"] == "income")
    old = f"FICTIONAL eligibility: annual income at most {threshold}."
    new_threshold = threshold + 1000
    from .db import uid

    new = f"FICTIONAL eligibility: annual income at most {new_threshold}.\nSynthetic source revision {uid()}"
    if not db.scalar(select(Snapshot).where(Snapshot.source_id == source.id)):
        ingest_snapshot(db, source, old)
    proposal = ingest_snapshot(db, source, new)
    rule["version"] = scheme.active_version + 1
    income = next(c for c in rule["conditions"] if c["id"] == "income")
    income["value"] = new_threshold
    income["description"] = f"Annual income is at most ₹{new_threshold:,}"
    income["description_kn"] = f"ವಾರ್ಷಿಕ ಆದಾಯ ₹{new_threshold:,} ಮೀರಬಾರದು"
    rule["clauses"]["demo:income"] = (
        f"FICTIONAL clause C: annual income at most INR {new_threshold}, evidenced within 366 days."
    )
    proposal.proposed_rule = rule
    proposal.regression_cases = publication_cases(new_threshold, date.today())
    db.commit()
    return proposal
