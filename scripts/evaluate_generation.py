"""Run the live generator on unreviewed development questions.

This checks whether a generated answer cites an author-specified source passage.
It does not score semantic correctness, legal currency or user safety.
"""

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research import ResearchIndex


def main():
    root = ROOT / "data" / "research"
    cases = json.loads((root / "development_queries.json").read_text())["cases"]
    index = ResearchIndex()
    annotations = {item["id"]: item for item in index.items if item["kind"] == "annotation"}
    results = []
    for case in cases:
        expected = set()
        for ref in case["relevant"]:
            expected.update(annotations[ref]["citations"] if ref in annotations else [ref])
        start = time.monotonic()
        answer = index.answer(case["question"], case["scheme_id"])
        cited = {c["id"] for c in answer["citations"]}
        result = {
            "id": case["id"], "status": answer["status"], "answer": answer["answer"],
            "expected_source_ids": sorted(expected), "cited_source_ids": sorted(cited),
            "expected_citation_hit": bool(expected & cited),
            "seconds": round(time.monotonic() - start, 2),
        }
        results.append(result)
        print(f"{case['id']}: {result['status']}, citation_hit={result['expected_citation_hit']}, {result['seconds']}s", flush=True)
    output = {
        "measured_at": datetime.now(UTC).isoformat(),
        "dataset_status": "12 author-generated development probes; no independent review",
        "provider": os.getenv("FORMFLOW_LLM_PROVIDER", "ollama"),
        "model": os.getenv("FORMFLOW_LLM_MODEL", "qwen3:4b"),
        "dense_model": os.getenv("FORMFLOW_EMBED_MODEL") or None,
        "reranker_model": os.getenv("FORMFLOW_RERANK_MODEL") or None,
        "citation_hits": sum(r["expected_citation_hit"] for r in results),
        "answer_count": sum(r["status"] == "grounded_generation" for r in results),
        "cases": results,
    }
    (root / "generation_evaluation.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {root / 'generation_evaluation.json'}", flush=True)


if __name__ == "__main__":
    main()
