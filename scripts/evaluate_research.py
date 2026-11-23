"""Small transparent development benchmark; does not assert population accuracy."""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.research import ResearchIndex

ROOT = Path(__file__).resolve().parents[1] / "data" / "research"
cases = json.loads((ROOT / "development_queries.json").read_text())["cases"]
index = ResearchIndex()
known = {item["id"] for item in index.items}
for case in cases:
    if not set(case["relevant"]) <= known:
        raise ValueError(f"Unresolved benchmark passage in {case['id']}")
results = {}
for mode in ("keyword", "dense", "hybrid", "hybrid_rerank"):
    if mode == "dense" and not os.getenv("FORMFLOW_EMBED_MODEL"):
        results[mode] = {"status": "not_run", "reason": "FORMFLOW_EMBED_MODEL is not configured"}
        continue
    if mode == "hybrid" and not os.getenv("FORMFLOW_EMBED_MODEL"):
        results[mode] = {"status": "not_run", "reason": "Dense model is not configured; keyword path is measured separately"}
        continue
    if mode == "hybrid_rerank" and not os.getenv("FORMFLOW_RERANK_MODEL"):
        results[mode] = {"status": "not_run", "reason": "FORMFLOW_RERANK_MODEL is not configured"}
        continue
    ranks = []
    start = time.perf_counter()
    for case in cases:
        hits = index.retrieve(case["question"], 10, case["scheme_id"], mode)
        rank = next((n for n, hit in enumerate(hits, 1) if hit["id"] in case["relevant"]), None)
        ranks.append(rank)
    elapsed = time.perf_counter() - start
    results[mode] = {"status": "run" if not index.model_error else "failed", "count": len(cases), "recall_at_5": round(sum(rank is not None and rank <= 5 for rank in ranks) / len(cases), 4), "mrr_at_10": round(sum(1 / rank for rank in ranks if rank) / len(cases), 4), "latency_ms_per_query": round(elapsed * 1000 / len(cases), 2), "ranks": ranks, "model_error": index.model_error}
citations_correct = 0
supported = 0
for case in cases:
    answer = index.answer(case["question"], case["scheme_id"])
    expected_source_ids = set()
    for relevant in case["relevant"]:
        item = next(i for i in index.items if i["id"] == relevant)
        expected_source_ids.update(item.get("citations", [relevant]))
    if answer["status"] != "insufficient_evidence":
        supported += 1
    if expected_source_ids & {c["id"] for c in answer["citations"]}:
        citations_correct += 1
results["extractive_answers"] = {"count": len(cases), "supported": supported, "expected_citation_hit_rate": round(citations_correct / len(cases), 4), "note": "Automatic check against author-generated development references; answer correctness not independently reviewed"}
report = {"dataset": "development_queries.json", "dataset_status": "author-generated, unreviewed development probes", "model": os.getenv("FORMFLOW_EMBED_MODEL") or None, "model_revision": os.getenv("FORMFLOW_EMBED_REVISION") or None, "reranker": os.getenv("FORMFLOW_RERANK_MODEL") or None, "reranker_revision": os.getenv("FORMFLOW_RERANK_REVISION") or None, "model_error": index.model_error, "results": results}
(ROOT / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
