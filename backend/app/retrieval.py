"""Clause-aware local ingestion. Retrieved text never determines a verdict."""

import hashlib
import re
from .db import Clause


def chunks(text, max_chars=1200):
    paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n|\n(?=\d+[.)])", text) if p.strip()]
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            yield paragraph
        else:
            words = paragraph.split()
            current = ""
            for word in words:
                if current and len(current) + len(word) + 1 > max_chars:
                    yield current
                    current = ""
                current = (current + " " + word).strip()
            if current:
                yield current


def index_source(db, source, text):
    ids = []
    for chunk in chunks(text):
        identifier = source.id + ":" + hashlib.sha256(chunk.encode()).hexdigest()[:24]
        has_kn = bool(re.search(r"[\u0c80-\u0cff]", chunk))
        has_en = bool(re.search(r"[a-zA-Z]", chunk))
        if not db.get(Clause, identifier):
            db.add(
                Clause(
                    id=identifier,
                    scheme_id=source.scheme_id,
                    text=chunk,
                    language="mixed" if has_kn and has_en else "kn" if has_kn else "en",
                )
            )
        ids.append(identifier)
    return ids
