"""Pure deterministic rule DSL. No IO, clock, network, LLM, eval or database calls."""

from __future__ import annotations

import operator
from datetime import date
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Truth(str, Enum):
    TRUE = "SATISFIED"
    FALSE = "NOT_SATISFIED"
    UNKNOWN = "INSUFFICIENT_EVIDENCE"


def kleene(op: str, values: list[Truth]) -> Truth:
    if op == "NOT":
        if len(values) != 1:
            raise ValueError("NOT requires exactly one child")
        return {Truth.TRUE: Truth.FALSE, Truth.FALSE: Truth.TRUE, Truth.UNKNOWN: Truth.UNKNOWN}[values[0]]
    if not values:
        raise ValueError("Empty logical expressions are forbidden")
    if op == "AND":
        return Truth.FALSE if Truth.FALSE in values else Truth.UNKNOWN if Truth.UNKNOWN in values else Truth.TRUE
    if op == "OR":
        return Truth.TRUE if Truth.TRUE in values else Truth.UNKNOWN if Truth.UNKNOWN in values else Truth.FALSE
    raise ValueError("Unknown logical operator")


FACTS = {
    "age": ("number", "years"),
    "annual_income": ("number", "INR/year"),
    "state": ("string", "text"),
    "disability_percentage": ("number", "percent"),
    "bpl": ("boolean", "boolean"),
    "existing_pension": ("boolean", "boolean"),
    "dob": ("date", "date"),
    "district": ("string", "text"),
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Condition(StrictModel):
    id: str = Field(min_length=1)
    description: str
    description_kn: str
    fact: str
    op: Literal["eq", "ne", "gt", "gte", "lt", "lte", "in", "range", "exists"]
    value: Any
    datatype: Literal["number", "string", "boolean", "date"]
    unit: str
    evidence_types: list[str] = Field(min_length=1)
    clause: str
    max_age_days: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def valid(self):
        if self.fact not in FACTS or FACTS[self.fact] != (self.datatype, self.unit):
            raise ValueError("Unknown fact or incompatible units")
        if self.value is None or not self.clause:
            raise ValueError("Value and source clause required")
        if self.op == "exists":
            if self.value is not True:
                raise ValueError("Existence conditions require value true")
            return self
        if self.op in ("gt", "gte", "lt", "lte", "range") and self.datatype not in ("number", "date"):
            raise ValueError("Ordered comparison requires numeric or date units")
        vals = self.value if self.op in ("in", "range") else [self.value]
        if not isinstance(vals, list) or not vals or (self.op == "range" and len(vals) != 2):
            raise ValueError("Invalid comparison values")
        for v in vals:
            normalize(v, self.datatype)
        if self.op == "range" and vals[0] > vals[1]:
            raise ValueError("Reversed range")
        return self


class Expression(StrictModel):
    op: Literal["AND", "OR", "NOT"]
    args: list[str | Expression] = Field(min_length=1)

    @model_validator(mode="after")
    def arity(self):
        if self.op == "NOT" and len(self.args) != 1:
            raise ValueError("NOT requires exactly one child")
        return self


class Rule(StrictModel):
    scheme_id: str
    version: int = Field(ge=1)
    mode: Literal["DEMO", "REVIEWED"]
    effective_from: date
    effective_to: date | None = None
    conditions: list[Condition] = Field(min_length=1)
    root: str | Expression
    clauses: dict[str, str]
    application_documents: list[str]

    @model_validator(mode="after")
    def references(self):
        ids = {c.id for c in self.conditions}
        if len(ids) != len(self.conditions):
            raise ValueError("Duplicate condition IDs")
        if any(c.clause not in self.clauses or not self.clauses[c.clause].strip() for c in self.conditions):
            raise ValueError("Unresolved source clause")

        def check(expr):
            if isinstance(expr, str):
                if expr not in ids:
                    raise ValueError("Undefined condition")
            else:
                for arg in expr.args:
                    check(arg)

        check(self.root)
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Invalid effective period")
        return self


def normalize(value, datatype):
    if datatype == "number":
        if isinstance(value, bool):
            raise ValueError("Boolean is not numeric evidence")
        result = float(str(value).replace(",", "").replace("₹", "").strip())
        if not __import__("math").isfinite(result):
            raise ValueError("Non-finite number")
        return result
    if datatype == "boolean":
        if value is True or str(value).lower() in ("true", "yes", "ಹೌದು"):
            return True
        if value is False or str(value).lower() in ("false", "no", "ಇಲ್ಲ"):
            return False
        raise ValueError("Invalid boolean")
    if datatype == "date":
        return date.fromisoformat(str(value))
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Invalid text")
    return value.strip().casefold()


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def compare(actual, op, expected):
    if op == "exists":
        return actual is not None
    if op == "in":
        return actual in expected
    if op == "range":
        return expected[0] <= actual <= expected[1]
    return {
        "eq": operator.eq,
        "ne": operator.ne,
        "gt": operator.gt,
        "gte": operator.ge,
        "lt": operator.lt,
        "lte": operator.le,
    }[op](actual, expected)


def evaluate(rule: Rule, facts: list[dict], today: date) -> dict:
    """Corrections remain unknown; confirmation means user review, never authentication."""
    results = []
    for c in rule.conditions:
        candidates = [f for f in facts if f["key"] == c.fact or (c.fact == "age" and f["key"] == "dob")]
        status, reason, values, usable = Truth.UNKNOWN, "MISSING_FIELD" if facts else "MISSING_DOCUMENT", [], []
        reasons = []
        for f in candidates:
            if f.get("document_type") not in c.evidence_types:
                reasons.append("UNSUPPORTED_DOCUMENT")
                continue
            if not f.get("document_id"):
                reasons.append("MISSING_DOCUMENT")
                continue
            try:
                issued = date.fromisoformat(f["issued_at"]) if f.get("issued_at") else None
                expires = date.fromisoformat(f["expires_at"]) if f.get("expires_at") else None
                if (expires and expires < today) or (
                    c.max_age_days and (not issued or (today - issued).days > c.max_age_days)
                ):
                    reasons.append("EXPIRED_DOCUMENT")
                    continue
                if issued and issued > today:
                    reasons.append("AMBIGUOUS_VALUE")
                    continue
                if f.get("review") == "corrected":
                    reasons.append("UNVERIFIED_CORRECTION")
                    continue
                if f.get("review") == "unreadable":
                    reasons.append("UNREADABLE")
                    continue
                if f.get("review") != "confirmed":
                    reasons.append("UNCONFIRMED_FIELD")
                    continue
                if f.get("confidence", 0) < 0.75:
                    reasons.append("LOW_OCR_CONFIDENCE")
                    continue
                v = (
                    age_on(date.fromisoformat(f["value"]), today)
                    if f["key"] == "dob" and c.fact == "age"
                    else normalize(f["value"], c.datatype)
                )
                values.append(v)
                usable.append(f)
            except (ValueError, TypeError, KeyError):
                reasons.append("AMBIGUOUS_VALUE")
        if len({str(v) for v in values}) > 1:
            reason = "CONFLICTING_EVIDENCE"
        elif values:
            expected = (
                True
                if c.op == "exists"
                else (
                    [normalize(v, c.datatype) for v in c.value]
                    if c.op in ("in", "range")
                    else normalize(c.value, c.datatype)
                )
            )
            status = Truth.TRUE if compare(values[0], c.op, expected) else Truth.FALSE
            reason = "CONDITION_MET" if status == Truth.TRUE else "CONDITION_NOT_MET"
        elif reasons:
            reason = reasons[0]
        if today < rule.effective_from or (rule.effective_to and today > rule.effective_to):
            status, reason = Truth.UNKNOWN, "RULE_NOT_EFFECTIVE"
        results.append(
            {
                "id": c.id,
                "description": c.description,
                "description_kn": c.description_kn,
                "status": status.value,
                "reason": reason,
                "fact": c.fact,
                "operator": c.op,
                "expected": c.value,
                "unit": c.unit,
                "actual": [str(v) for v in values],
                "fact_ids": [f.get("id") for f in candidates],
                "evidence": [
                    {k: f.get(k) for k in ("id", "document_id", "page", "bbox", "method", "review")} for f in candidates
                ],
                "clause_id": c.clause,
                "clause_text": rule.clauses[c.clause],
                "rule_version": rule.version,
                "required_documents": c.evidence_types if status == Truth.UNKNOWN else [],
            }
        )
    by_id = {r["id"]: Truth(r["status"]) for r in results}

    def resolve(expr):
        return by_id[expr] if isinstance(expr, str) else kleene(expr.op, [resolve(a) for a in expr.args])

    root = resolve(rule.root)
    checklist = []
    for typ in sorted({t for c in rule.conditions for t in c.evidence_types}):
        relevant = [r for r, c in zip(results, rule.conditions) if typ in c.evidence_types]
        unknown = [r for r in relevant if r["status"] == Truth.UNKNOWN.value]
        group = (
            "provided"
            if not unknown
            else "conflicting_or_outdated"
            if any(r["reason"] in ("CONFLICTING_EVIDENCE", "EXPIRED_DOCUMENT") for r in unknown)
            else "clarification"
            if any(r["evidence"] for r in unknown)
            else "required"
        )
        checklist.append(
            {
                "document_type": typ,
                "group": group,
                "conditions": [r["id"] for r in relevant],
                "reasons": sorted({r["reason"] for r in relevant}),
                "replacement": group == "conflicting_or_outdated",
            }
        )
    for typ in rule.application_documents:
        checklist.append(
            {
                "document_type": typ,
                "group": "application",
                "conditions": [],
                "reasons": ["FINAL_APPLICATION_ONLY"],
                "replacement": False,
            }
        )
    return {
        "scheme_id": rule.scheme_id,
        "version": rule.version,
        "mode": rule.mode,
        "date": today.isoformat(),
        "verdict": {Truth.TRUE: "LIKELY_ELIGIBLE", Truth.UNKNOWN: "NEEDS_EVIDENCE", Truth.FALSE: "NOT_ELIGIBLE"}[root],
        "conditions": results,
        "checklist": checklist,
        "evidence_guidance": minimal_evidence_set(results),
        "disclaimer": "Preliminary guidance only. Not a government decision. DEMO rules are fictional.",
    }


def minimal_evidence_set(conditions):
    """Exact minimum set cover for unresolved conditions and mapped document types.

    An unknown effective rule or unmapped condition cannot be fixed by uploading
    another document, so it remains explicitly unresolved.
    """
    from itertools import combinations

    unresolved = [c for c in conditions if c["status"] == Truth.UNKNOWN.value]
    needed = {c["id"] for c in unresolved}
    mapping = {}
    for condition in unresolved:
        if condition.get("reason") == "RULE_NOT_EFFECTIVE":
            continue
        for document_type in condition.get("required_documents", []):
            mapping.setdefault(document_type, set()).add(condition["id"])
    impossible = sorted(needed - set().union(*mapping.values())) if mapping else sorted(needed)
    target = needed - set(impossible)
    selected = []
    for size in range(1, len(mapping) + 1):
        choices = [choice for choice in combinations(sorted(mapping), size) if set().union(*(mapping[c] for c in choice)) >= target]
        if choices:
            selected = list(choices[0])
            break
    return {
        "unresolved_conditions": sorted(needed),
        "documents": [{"document_type": name, "resolves": sorted(mapping[name] & target), "why": "One accepted document category may support each listed condition; facts still require review"} for name in selected],
        "no_sufficient_mapping": impossible,
        "method": "exact minimum document-type set cover; documents are guidance, not proof of eligibility",
    }


def rank(results):
    return sorted(
        results,
        key=lambda r: (
            {"LIKELY_ELIGIBLE": 0, "NEEDS_EVIDENCE": 1, "NOT_ELIGIBLE": 2}[r["verdict"]],
            len({i["document_type"] for i in r["checklist"] if i["group"] not in ("provided", "application")}),
            r["scheme_id"],
        ),
    )


def validate_explanation(candidate: dict, result: dict) -> bool:
    # Free-form output is never accepted. Only an exact structured projection is allowed.
    expected = {
        "verdict": result["verdict"],
        "conditions": [{k: c[k] for k in ("id", "status", "expected", "clause_id")} for c in result["conditions"]],
    }
    return candidate == expected
