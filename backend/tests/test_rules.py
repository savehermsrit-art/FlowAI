from copy import deepcopy
from datetime import date

import pytest
from pydantic import ValidationError
from app.demo import demo_rule
from app.evaluation import evidence, golden_cases, run_evaluation
from app.rules import Rule, Truth, age_on, compare, evaluate, kleene, normalize, rank, validate_explanation

T, F, U = Truth.TRUE, Truth.FALSE, Truth.UNKNOWN


@pytest.mark.parametrize(
    "a,b,expected_and,expected_or",
    [
        (T, T, T, T),
        (T, F, F, T),
        (T, U, U, T),
        (F, T, F, T),
        (F, F, F, F),
        (F, U, F, U),
        (U, T, U, T),
        (U, F, F, U),
        (U, U, U, U),
    ],
)
def test_kleene(a, b, expected_and, expected_or):
    assert kleene("AND", [a, b]) == expected_and
    assert kleene("OR", [a, b]) == expected_or


@pytest.mark.parametrize("a,expected", [(T, F), (F, T), (U, U)])
def test_not(a, expected):
    assert kleene("NOT", [a]) == expected


@pytest.mark.parametrize("op,values", [("AND", []), ("OR", []), ("NOT", []), ("NOT", [T, F]), ("X", [T])])
def test_invalid_logic(op, values):
    with pytest.raises(ValueError):
        kleene(op, values)


@pytest.mark.parametrize(
    "actual,op,value,expected",
    [
        (4, "eq", 4, True),
        (4, "eq", 5, False),
        (4, "ne", 5, True),
        (4, "gt", 4, False),
        (4, "gt", 3, True),
        (4, "gte", 4, True),
        (4, "lt", 5, True),
        (4, "lte", 4, True),
        (4, "in", [3, 4], True),
        (4, "range", [4, 6], True),
        (6, "range", [4, 6], True),
        (7, "range", [4, 6], False),
        (4, "exists", True, True),
    ],
)
def test_comparisons(actual, op, value, expected):
    assert compare(actual, op, value) is expected


@pytest.mark.parametrize("case", golden_cases(), ids=lambda c: c["id"])
def test_golden(case):
    r = evaluate(Rule.model_validate(demo_rule()), deepcopy(case["facts"]), date.fromisoformat(case["date"]))
    assert r["verdict"] == case["expected"]
    assert [c["status"] for c in r["conditions"]] == case["conditions"]
    missing = {i["document_type"] for i in r["checklist"] if i["group"] not in ("provided", "application")}
    assert missing == set(case["missing"])
    assert len(r["checklist"]) == len({i["document_type"] for i in r["checklist"]})


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["conditions"][0].update(value=None),
        lambda r: r["conditions"][0].update(fact="invented"),
        lambda r: r["conditions"][0].update(unit="months"),
        lambda r: r["conditions"][0].update(clause="unknown"),
        lambda r: r["conditions"][0].update(value="sixty"),
        lambda r: r["conditions"][0].update(op="eval"),
        lambda r: r.update(root="absent"),
        lambda r: r.update(effective_from="invalid"),
        lambda r: r.update(root={"op": "NOT", "args": ["age", "income"]}),
        lambda r: r["conditions"].append(deepcopy(r["conditions"][0])),
        lambda r: r["conditions"][0].update(evidence_types=[]),
        lambda r: r.update(surprise=True),
    ],
)
def test_rule_validation(mutate):
    r = demo_rule()
    mutate(r)
    with pytest.raises(ValidationError):
        Rule.model_validate(r)


def test_nested_false_dominates_missing():
    r = demo_rule()
    r["root"] = {"op": "AND", "args": ["age", {"op": "OR", "args": ["income", "residence"]}]}
    assert evaluate(Rule.model_validate(r), evidence(age=59)[:1], date(2026, 11, 17))["verdict"] == "NOT_ELIGIBLE"
    r["root"] = {"op": "NOT", "args": ["income"]}
    assert evaluate(Rule.model_validate(r), [], date(2026, 11, 17))["verdict"] == "NEEDS_EVIDENCE"


def test_dates_and_dob():
    assert age_on(date(1966, 11, 18), date(2026, 11, 17)) == 59
    assert age_on(date(1966, 11, 17), date(2026, 11, 17)) == 60
    assert age_on(date(1964, 2, 29), date(2025, 2, 28)) == 60
    fs = evidence()
    fs[0].update(key="dob", value="1956-01-01")
    assert evaluate(Rule.model_validate(demo_rule()), fs, date(2026, 11, 17))["verdict"] == "LIKELY_ELIGIBLE"


def test_rule_version_and_purity():
    facts = evidence()
    original = deepcopy(facts)
    r = Rule.model_validate(demo_rule())
    result = evaluate(r, facts, date(2026, 11, 17))
    assert result == evaluate(r, facts, date(2026, 11, 17)) and facts == original
    modified = demo_rule(version=2)
    modified["conditions"][2]["value"] = 20000
    assert evaluate(Rule.model_validate(modified), facts, date(2026, 11, 17))["verdict"] == "NOT_ELIGIBLE"
    assert result["version"] == 1


def test_normalization():
    assert normalize("₹ 30,000", "number") == 30000
    assert normalize(" Karnataka ", "string") == "karnataka"
    assert normalize("ಹೌದು", "boolean") is True
    for bad in (True, "NaN", "Infinity", "unknown"):
        with pytest.raises(ValueError):
            normalize(bad, "number")


def test_ranking_and_explanation():
    rule = Rule.model_validate(demo_rule())
    a = evaluate(rule, evidence(), date(2026, 11, 17))
    b = evaluate(rule, [], date(2026, 11, 17))
    c = evaluate(rule, evidence(age=45), date(2026, 11, 17))
    d = evaluate(rule, evidence()[:2], date(2026, 11, 17))
    assert rank([c, b, a, d]) == [a, d, b, c]
    projection = {
        "verdict": a["verdict"],
        "conditions": [{k: c[k] for k in ("id", "status", "expected", "clause_id")} for c in a["conditions"]],
    }
    assert validate_explanation(projection, a)
    projection["conditions"][0]["expected"] = 45
    assert not validate_explanation(projection, a)


def test_metrics():
    r = run_evaluation()
    assert r["count"] == 52 and r["scheme_accuracy"] == 1 and r["condition_accuracy"] == 1
    assert r["incorrect_positive"] == r["incorrect_negative"] == 0


def test_existence_dsl_and_ordered_type_validation():
    rule = demo_rule()
    rule["conditions"][0].update(op="exists", value=True)
    result = evaluate(Rule.model_validate(rule), evidence(), date(2026, 11, 17))
    assert result["conditions"][0]["status"] == "SATISFIED"
    rule["conditions"][1].update(op="gt")
    with pytest.raises(ValidationError):
        Rule.model_validate(rule)
