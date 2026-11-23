"""Evaluate the set-cover component on transparent synthetic development cases."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.rules import minimal_evidence_set

ROOT = Path(__file__).resolve().parents[1] / "data" / "research"
cases = json.loads((ROOT / "evidence_cases.json").read_text())["cases"]
details = []
tp = fp = fn = 0
for case in cases:
    result = minimal_evidence_set(case["conditions"])
    actual = {item["document_type"] for item in result["documents"]}
    expected = set(case["expected_documents"])
    tp += len(actual & expected)
    fp += len(actual - expected)
    fn += len(expected - actual)
    details.append({"id": case["id"], "documents": sorted(actual), "expected": sorted(expected), "unmapped_correct": result["no_sufficient_mapping"] == case["expected_unmapped"], "minimum_size_correct": len(actual) == len(expected)})
report = {"dataset": "evidence_cases.json", "status": "synthetic development only", "count": len(cases), "precision": tp / (tp + fp) if tp + fp else 1.0, "recall": tp / (tp + fn) if tp + fn else 1.0, "unmapped_correct": sum(d["unmapped_correct"] for d in details), "minimum_size_correct": sum(d["minimum_size_correct"] for d in details), "details": details}
(ROOT / "evidence_evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
