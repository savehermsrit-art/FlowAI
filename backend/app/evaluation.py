"""Independent test labels: see docs/EVALUATION_SPEC.md. No expected label calls engine."""

import json
from datetime import date
from pathlib import Path
from .demo import demo_rule
from .rules import Rule, evaluate, validate_explanation


def evidence(age=70, income=30000, state="Karnataka", today=date(2026, 11, 17)):
    return [
        {
            "id": key,
            "key": key,
            "value": str(value),
            "document_id": "synthetic-" + key,
            "document_type": typ,
            "review": "confirmed",
            "confidence": 1,
            "issued_at": today.isoformat(),
            "method": "synthetic test",
        }
        for key, value, typ in [
            ("age", age, "age_proof"),
            ("annual_income", income, "income"),
            ("state", state, "residence"),
        ]
    ]


def publication_cases(threshold, today):
    return [
        {"facts": evidence(income=threshold, today=today), "date": today.isoformat(), "expected": "LIKELY_ELIGIBLE"},
        {"facts": evidence(income=threshold + 1, today=today), "date": today.isoformat(), "expected": "NOT_ELIGIBLE"},
        {"facts": evidence(age=59, today=today), "date": today.isoformat(), "expected": "NOT_ELIGIBLE"},
        {"facts": evidence(today=today)[:1], "date": today.isoformat(), "expected": "NEEDS_EVIDENCE"},
    ]


def golden_cases():
    cases = []
    # Explicit independent specification: age >= 60, Karnataka, income <= 50000, current confirmed evidence.
    definitions = [
        ("eligible", evidence(), "LIKELY_ELIGIBLE", ["SATISFIED"] * 3, []),
        ("age_boundary", evidence(age=60), "LIKELY_ELIGIBLE", ["SATISFIED"] * 3, []),
        ("income_boundary", evidence(income=50000), "LIKELY_ELIGIBLE", ["SATISFIED"] * 3, []),
        ("under_age", evidence(age=59), "NOT_ELIGIBLE", ["NOT_SATISFIED", "SATISFIED", "SATISFIED"], []),
        ("over_income", evidence(income=50001), "NOT_ELIGIBLE", ["SATISFIED", "SATISFIED", "NOT_SATISFIED"], []),
        ("other_state", evidence(state="Kerala"), "NOT_ELIGIBLE", ["SATISFIED", "NOT_SATISFIED", "SATISFIED"], []),
        (
            "missing_income",
            [f for f in evidence() if f["key"] != "annual_income"],
            "NEEDS_EVIDENCE",
            ["SATISFIED", "SATISFIED", "INSUFFICIENT_EVIDENCE"],
            ["income"],
        ),
        ("no_evidence", [], "NEEDS_EVIDENCE", ["INSUFFICIENT_EVIDENCE"] * 3, ["age_proof", "residence", "income"]),
    ]
    conflict = evidence() + [dict(evidence()[1], id="conflict-income", value="70000")]
    definitions.append(
        ("conflict", conflict, "NEEDS_EVIDENCE", ["SATISFIED", "SATISFIED", "INSUFFICIENT_EVIDENCE"], ["income"])
    )
    for field, value, tag in [
        ("review", "unconfirmed", "unconfirmed"),
        ("review", "corrected", "incorrect_ocr_correction"),
        ("confidence", 0.3, "blurred"),
        ("expires_at", "2025-01-01", "expired"),
    ]:
        fs = evidence()
        fs[1][field] = value
        definitions.append((tag, fs, "NEEDS_EVIDENCE", ["SATISFIED", "SATISFIED", "INSUFFICIENT_EVIDENCE"], ["income"]))
    # 52 individually identified cases across four fixture-language/quality strata.
    for stratum in ("english_clear", "kannada", "mixed", "photo"):
        for name, fs, expected, conditions, missing in definitions:
            cases.append(
                {
                    "id": stratum + ":" + name,
                    "facts": fs,
                    "expected": expected,
                    "conditions": conditions,
                    "missing": missing,
                    "date": "2026-11-17",
                    "stratum": stratum,
                }
            )
    return cases


def run_evaluation():
    rule = Rule.model_validate(demo_rule())
    rows = []
    condition_correct = verdict_correct = true_positive = predicted = relevant = explanation_pass = 0
    incorrect_positive = incorrect_negative = duplicates = citations_correct = 0
    for case in golden_cases():
        result = evaluate(rule, case["facts"], date.fromisoformat(case["date"]))
        ok = result["verdict"] == case["expected"]
        verdict_correct += ok
        condition_correct += sum(
            c["status"] == expected for c, expected in zip(result["conditions"], case["conditions"])
        )
        actual_missing = [
            c["document_type"] for c in result["checklist"] if c["group"] not in ("provided", "application")
        ]
        true_positive += len(set(actual_missing) & set(case["missing"]))
        predicted += len(actual_missing)
        relevant += len(case["missing"])
        duplicates += len(actual_missing) - len(set(actual_missing))
        projection = {
            "verdict": result["verdict"],
            "conditions": [{k: c[k] for k in ("id", "status", "expected", "clause_id")} for c in result["conditions"]],
        }
        explanation_pass += validate_explanation(projection, result)
        citations_correct += sum(c["clause_text"] == rule.clauses.get(c["clause_id"]) for c in result["conditions"])
        incorrect_positive += result["verdict"] == "LIKELY_ELIGIBLE" and case["expected"] != "LIKELY_ELIGIBLE"
        incorrect_negative += result["verdict"] == "NOT_ELIGIBLE" and case["expected"] != "NOT_ELIGIBLE"
        rows.append({"id": case["id"], "expected": case["expected"], "actual": result["verdict"], "passed": ok})
    n = len(rows)
    return {
        "dataset": "52 synthetic fact-level cases; language labels are strata, NOT OCR measurements",
        "count": n,
        "scheme_accuracy": verdict_correct / n,
        "condition_accuracy": condition_correct / (n * 3),
        "checklist_precision": true_positive / predicted if predicted else 1,
        "checklist_recall": true_positive / relevant if relevant else 1,
        "incorrect_positive": incorrect_positive,
        "incorrect_negative": incorrect_negative,
        "duplicate_requests": duplicates,
        "explanation_validator_pass_rate": explanation_pass / n,
        "citation_correctness": citations_correct / (n * 3),
        "template_fallback_frequency": 1.0,
        "human_agreement": None,
        "ocr_metrics": "Separate executable OCR benchmark; not inferred from fact-level tests",
        "cases": rows,
    }


if __name__ == "__main__":
    output = Path("data/evaluation.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(run_evaluation(), indent=2), encoding="utf-8")
    print(output.resolve())
