"""Versioned public-source retrieval and conservative extractive answers.

Source text is data. No instruction or URL found inside a page is executed.
Dense and reranker models are optional and lazy so the default CPU path starts
without large downloads; model errors are returned as visible status.
"""

import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[2] / "data" / "research"
STOP = {"what", "which", "where", "how", "the", "for", "and", "can", "does", "is", "are", "a", "an", "of", "to", "in", "i", "my", "scheme", "pension", "tell", "me"}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourcedField(Strict):
    value: str = Field(min_length=1)
    passages: list[str] = Field(min_length=1)


class ResearchScheme(Strict):
    id: str
    name: str
    name_kn: str
    primary_url: str
    department: str
    review_status: str
    assessment_enabled: bool
    source_version_policy: str
    eligibility: list[SourcedField] = Field(min_length=1)
    exceptions: list[SourcedField]
    benefits: list[SourcedField]
    application_documents: list[SourcedField]
    application: list[SourcedField]
    unresolved: list[str]


class DraftCondition(Strict):
    id: str
    fact: str
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte", "in", "range"]
    value: bool | int | float | str | list[str] | list[int]
    unit: str
    passages: list[str] = Field(min_length=1)
    evidence_types: list[str]

    @model_validator(mode="after")
    def operator_units(self):
        if self.operator in ("gt", "gte", "lt", "lte", "range") and self.unit not in ("years", "INR", "INR/year"):
            raise ValueError("Ordered draft condition needs a numeric unit")
        if self.operator == "range" and (not isinstance(self.value, list) or len(self.value) != 2 or self.value[0] > self.value[1]):
            raise ValueError("Invalid draft range")
        return self


class DraftRuleGroup(Strict):
    scheme_id: str
    logic: Literal["AND", "OR"]
    conditions: list[DraftCondition] = Field(min_length=1)
    unsupported_criteria: list[str]


class DraftMappings(Strict):
    version: str
    review_status: str
    effective_from: str | None
    groups: list[DraftRuleGroup] = Field(min_length=1)


def terms(text):
    lower = text.casefold()
    words = [w for w in re.findall(r"[^\W_]+", lower, re.UNICODE) if w not in STOP and len(w) > 1]
    letters = "".join(c for c in lower if c.isalnum() or "\u0c80" <= c <= "\u0cff")
    grams = [letters[i:i + 3] for i in range(max(0, len(letters) - 2))]
    return words + grams


def load_corpus(root=ROOT):
    manifest = json.loads((root / "manifest.json").read_text())
    passages = json.loads((root / "passages.json").read_text())
    schemes = [ResearchScheme.model_validate(s).model_dump() for s in json.loads((root / "schemes.json").read_text())]
    sources = {s["id"]: s for s in manifest}
    ids = {p["id"] for p in passages}
    for source in manifest:
        if source["status"] == "fetched":
            raw = (root / source["raw_path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source["content_hash"]:
                raise ValueError(f"Content hash mismatch for {source['id']}")
    for scheme in schemes:
        for category in ("eligibility", "exceptions", "benefits", "application_documents", "application"):
            for field in scheme[category]:
                if any(ref not in ids for ref in field["passages"]):
                    raise ValueError(f"Unresolved source reference in {scheme['id']}")
    mappings = DraftMappings.model_validate_json((root / "rule_mappings.json").read_text())
    for group in mappings.groups:
        if group.scheme_id not in {s["id"] for s in schemes}:
            raise ValueError(f"Unknown scheme in draft mapping {group.scheme_id}")
        for condition in group.conditions:
            if any(ref not in ids for ref in condition.passages):
                raise ValueError(f"Unresolved source clause for {condition.id}")
    return sources, passages, schemes


class ResearchIndex:
    def __init__(self, root=ROOT):
        self.sources, self.passages, self.schemes = load_corpus(root)
        self.items = []
        for passage in self.passages:
            if len(passage["text"]) >= 8:
                self.items.append(dict(passage, kind="source"))
        for scheme in self.schemes:
            for category in ("eligibility", "exceptions", "benefits", "application_documents", "application"):
                for n, field in enumerate(scheme[category]):
                    self.items.append({"id": f"field:{scheme['id']}:{category}:{n}", "scheme_id": scheme["id"], "text": f"{scheme['name']} — {field['value']}", "language": "en", "kind": "annotation", "category": category, "citations": field["passages"], "url": scheme["primary_url"], "section": category, "version": "curation-v1"})
        self.document_terms = [Counter(terms(item["text"])) for item in self.items]
        self.df = Counter(t for doc in self.document_terms for t in doc)
        self.average_length = sum(sum(d.values()) for d in self.document_terms) / max(1, len(self.items))
        self.model = None
        self.vectors = None
        self.reranker = None
        self.model_error = None

    def keyword(self, query, limit=30, scheme_id=None):
        query_terms = set(terms(query))
        scores = []
        count = len(self.items)
        for index, doc in enumerate(self.document_terms):
            if scheme_id and self.items[index]["scheme_id"] != scheme_id:
                continue
            length = sum(doc.values())
            score = 0.0
            for term in query_terms:
                if term not in doc:
                    continue
                idf = math.log(1 + (count - self.df[term] + 0.5) / (self.df[term] + 0.5))
                score += idf * doc[term] * 2.2 / (doc[term] + 1.2 * (0.25 + 0.75 * length / max(1, self.average_length)))
            if score > 0:
                scores.append((index, score))
        return sorted(scores, key=lambda x: (-x[1], self.items[x[0]]["id"]))[:limit]

    def _dense(self, query, limit, scheme_id):
        model_name = os.getenv("FORMFLOW_EMBED_MODEL", "").strip()
        if not model_name:
            return []
        try:
            if self.model is None:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_name, revision=os.getenv("FORMFLOW_EMBED_REVISION") or None)
                self.vectors = self.model.encode([i["text"] for i in self.items], normalize_embeddings=True, show_progress_bar=False)
            q = self.model.encode([query], normalize_embeddings=True)[0]
            scored = [(n, float(vector @ q)) for n, vector in enumerate(self.vectors) if not scheme_id or self.items[n]["scheme_id"] == scheme_id]
            return sorted(scored, key=lambda x: (-x[1], self.items[x[0]]["id"]))[:limit]
        except Exception as exc:
            self.model_error = f"Dense model unavailable: {type(exc).__name__}: {str(exc)[:160]}"
            return []

    def _rerank(self, query, candidates):
        name = os.getenv("FORMFLOW_RERANK_MODEL", "").strip()
        if not name or not candidates:
            return candidates
        try:
            if self.reranker is None:
                from sentence_transformers import CrossEncoder
                self.reranker = CrossEncoder(name, revision=os.getenv("FORMFLOW_RERANK_REVISION") or None)
            scores = self.reranker.predict([(query, self.items[n]["text"]) for n, _ in candidates])
            return sorted([(n, float(s)) for (n, _), s in zip(candidates, scores)], key=lambda x: (-x[1], self.items[x[0]]["id"]))
        except Exception as exc:
            self.model_error = f"Reranker unavailable: {type(exc).__name__}: {str(exc)[:160]}"
            return candidates

    def retrieve(self, query, limit=6, scheme_id=None, mode="hybrid"):
        keyword = self.keyword(query, scheme_id=scheme_id) if mode != "dense" else []
        dense = self._dense(query, 30, scheme_id) if mode != "keyword" else []
        if mode == "dense" and not dense:
            return []
        ranks = defaultdict(float)
        for ranking in (keyword, dense):
            for position, (index, _) in enumerate(ranking, 1):
                ranks[index] += 1 / (60 + position)
        candidates = sorted(ranks.items(), key=lambda x: (-x[1], self.items[x[0]]["id"]))[:10]
        if mode == "hybrid_rerank":
            candidates = self._rerank(query, candidates)
        return [dict(self.items[index], score=score) for index, score in candidates[:limit]]

    def answer(self, query, scheme_id=None):
        lower = query.casefold()
        kannada = bool(re.search("[\u0c80-\u0cff]", query))
        if not scheme_id:
            for name, identifier in (("sandhya", "ka-sandhya"), ("ಸಂಧ್ಯಾ", "ka-sandhya"), ("widow", "ka-widow"), ("ವಿಧವಾ", "ka-widow"), ("old age", "ka-ignoaps"), ("indira", "ka-ignoaps"), ("ವೃದ್ಧಾಪ್ಯ", "ka-ignoaps")):
                if name in lower:
                    scheme_id = identifier
                    break
        hits = self.retrieve(query, 8, scheme_id, mode="hybrid_rerank")
        def matches(*words):
            return any(word in lower for word in words)
        category = None
        wanted = None
        if matches("document", "proof", "certificate", "ದಾಖಲೆ", "ಪ್ರಮಾಣ", "ಆಧಾರ್"):
            category = "application_documents"
        elif matches("apply", "application", "where", "ಅರ್ಜಿ", "ಸಲ್ಲಿಸ"):
            category = "application"
        elif matches("amount", "benefit", "how much", "ಮೊತ್ತ", "ಮಾಸಾಶನ"):
            category = "benefits"
        elif matches("remarry", "exclusion", "excluded", "ಹೊರತ", "ಪುನರ್ವಿವಾಹ"):
            category = "exceptions"
        elif matches("income", "ಆದಾಯ"):
            category = "eligibility"
            wanted = "income"
        elif matches("deposit", "savings", "ಠೇವಣಿ"):
            category = "eligibility"
            wanted = "deposit"
        elif matches("age", "old", "ವಯಸ್ಸು", "ವರ್ಷ"):
            category = "eligibility"
            wanted = "age"
        elif matches("eligible", "eligibility", "condition", "ಅರ್ಹತೆ", "ಮಾನದಂಡ"):
            category = "eligibility"
        elif matches("pension", "other pension", "private source", "ಖಾಸಗಿ"):
            category = "eligibility"
            wanted = "pension"
        if not scheme_id or not category:
            message = "ಯೋಜನೆಯನ್ನು ಆರಿಸಿ ಮತ್ತು ವಯಸ್ಸು, ಆದಾಯ, ಅರ್ಹತೆ, ಹೊರತಾಗಿರುವವರು, ಪ್ರಯೋಜನ ಅಥವಾ ದಾಖಲೆಗಳ ಬಗ್ಗೆ ಕೇಳಿ. ಈ ಪ್ರಶ್ನೆಗೆ ಸಾಕಷ್ಟು ಮೂಲ ಮಾಹಿತಿ ಇಲ್ಲ." if kannada else "Choose a scheme and ask about age, income, eligibility, exceptions, benefits, application or documents. The source does not support an answer to this question."
            return {"answer": message, "citations": [], "status": "insufficient_evidence", "model_status": self.model_error or "source linked research annotations active", "passages": hits}
        scheme = next(s for s in self.schemes if s["id"] == scheme_id)
        best = [f for f in scheme[category] if wanted is None or wanted in f["value"].casefold()]
        passage_by_id = {p["id"]: p for p in self.passages}
        citations = []
        for field in best:
            for ref in field["passages"]:
                p = passage_by_id[ref]
                if ref not in {c["id"] for c in citations}:
                    citations.append({"id": ref, "url": p["url"], "section": p["section"], "page": p["page"], "text": p["text"], "source_version": p["version"]})
        if not best:
            message = "ಈ ಪ್ರಶ್ನೆಗೆ ಉತ್ತರಿಸಲು ಸಂಗ್ರಹಿಸಿದ ಅಧಿಕೃತ ಮೂಲಗಳಲ್ಲಿ ಸಾಕಷ್ಟು ಪರಿಶೀಲಿತ ಮಾಹಿತಿ ಇಲ್ಲ." if kannada else "The collected official sources do not provide enough checked information to answer this question."
            return {"answer": message, "citations": [], "status": "insufficient_evidence", "model_status": self.model_error or "keyword retrieval active; dense model not configured", "passages": hits}
        answer = " ".join(passage_by_id[ref]["text"] for f in best for ref in f["passages"]) if kannada else " ".join(f["value"] for f in best)
        return {"answer": answer, "citations": citations, "status": "source_linked_research_annotation", "model_status": self.model_error or ("hybrid retrieval active" if os.getenv("FORMFLOW_EMBED_MODEL") else "keyword retrieval active; dense model not configured"), "passages": hits}
