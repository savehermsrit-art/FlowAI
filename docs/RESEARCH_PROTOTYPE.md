# FormFlow research prototype: implementation and limits

## Implementation plan and status

1. Inspect the existing demo, rules, OCR, tests and Docker stack — complete.
2. Archive a bounded set of official Karnataka pages and linked orders — complete for 11 sources, with raw bytes, hashes, extraction status and version records.
3. Curate source-linked scheme fields and draft condition mappings — complete for three schemes, pending independent review.
4. Add English/Kannada retrieval, cited guidance and development evaluation — implemented and run on this machine. The answer path is conservative, extractive generation from source-linked annotations; it is not an open-ended LLM.
5. Extend evidence guidance and source-change impact — implemented for the existing fictional assessment; tested on synthetic cases.
6. Verify the full Docker OCR/browser journeys — complete. Activate complete real rules and obtain independently reviewed datasets — outstanding for the reasons below.

## Sources and data lineage

The [Chitradurga district page](https://chitradurga.nic.in/en/scheme/ssp-en/) lists pensions and application locations. The [Vijayapura district page](https://vijayapura.nic.in/en/service/social-security-pensions/) confirms the programme list. The Karnataka Directorate's pages provide [old age pension](https://dssp.karnataka.gov.in/dssp/IndiraGandhiPension.aspx), [Sandhya Suraksha](https://dssp.karnataka.gov.in/dssp/Sandhya_Suraksha.aspx) and [widow pension](https://dssp.karnataka.gov.in/dssp/Widow_Scheme.aspx) conditions. Its [old age](https://dssp.karnataka.gov.in/dssp/OAP_Orders.aspx) and [Sandhya](https://dssp.karnataka.gov.in/dssp/SSY_Orders.aspx) order indexes and three linked PDFs are archived as well. The source list is deliberately bounded in `data/research/sources.json`; it does not crawl arbitrary links.

`scripts/ingest_official.py` checks an HTTPS host allowlist, refuses redirects, limits responses to 8 MB, records failures and pauses between requests. `data/research/manifest.json` records URL, title, department, language, retrieval time, SHA-256, content-addressed version, dates only when explicit, extraction status and raw path. Raw HTML/PDF bytes are in `data/research/raw/`; immutable per-source metadata and passages are in `data/research/versions/`. `attempts.jsonl` logs runs. Re-running the collector preserves old raw versions. It will not silently substitute demo content after a fetch failure.

HTML passages retain section and source version. PDF passages retain page when extraction is usable. All three downloaded Kannada PDFs yielded corrupted legacy-font text from embedded extraction; they are archived but **excluded from the searchable passage set**. Their orders therefore have not been interpreted. The directorate page's “last updated” date is metadata about the page, not proof that every rule on it is in force. No effective date is inferred from the crawl timestamp.

`schemes.json` contains source-linked eligibility, exceptions, benefit statements, application documents and instructions. `rule_mappings.json` contains **15 draft condition mappings**, including strict versus inclusive thresholds and units. Their `effective_from` is null, unmapped evidence is explicit, and `assessment_enabled` is false. `scripts/build_scheme_records.py` refuses to rebuild annotations if an expected passage changes, forcing review. Pydantic validates field and mapping structure, and `load_corpus()` checks every citation and raw content hash. These records are machine-assisted research annotations, not independently approved current rules. A document requested for an application is stored separately from an eligibility condition.

## System architecture

The existing path remains Next.js → FastAPI → PostgreSQL/SQLite → deterministic rule engine, with Celery/Redis and encrypted MinIO for OCR jobs in Compose. The new research path reads the versioned archive, ranks Unicode word and character terms, optionally loads multilingual dense embeddings, fuses rankings with reciprocal rank fusion, and optionally reranks ten candidates. English questions search English source-linked annotations; Kannada questions can return original Kannada passages. The answer generator selects only curated fields with resolved passage IDs, displays clickable official URLs and abstains when scheme or intent is unsupported. External source text never supplies tool instructions.

For this 128-passage corpus, an in-process dense matrix is simpler than pgvector. PostgreSQL's `simple` full-text index remains for the legacy source-clause search; the new Unicode-aware character index handles Kannada without assuming English word boundaries. BGE M3 is a [multilingual dense retrieval candidate](https://huggingface.co/BAAI/bge-m3); the [bge-reranker-v2-m3 model card](https://huggingface.co/BAAI/bge-reranker-v2-m3) documents the `CrossEncoder` API used here. Models load lazily and failures return a visible status with the keyword path available. The default Compose path does not download model weights. No local or external LLM provider is configured, so answer quality is limited to curated topics.

The existing rule evaluator distinguishes satisfied, failed and insufficient-evidence conditions, retains document provenance and blocks unsupported fact categories. The new `minimal_evidence_set` computes exact minimum set cover over mapped document categories for unresolved conditions. It explains when one category can address multiple conditions and flags conditions with no mapping or a non-effective rule. It guides collection; it does not turn a missing applicant fact into a falsehood. Source change proposals now conservatively list potentially affected conditions and historical assessment IDs. The flag requires human clause review before any rule publication or reassessment.

## Reproduce locally

Python 3.11+ and Node 24 were used for host research work on this 16 GB Apple Silicon machine. The existing Colima Docker profile was started and the full Compose stack was built and checked. The older README also explains the Windows Docker demo. The checked-in archive is available without another network fetch.

```bash
uv venv --python python3.11 .venv
uv pip install --python .venv/bin/python -r backend/requirements.txt
.venv/bin/python scripts/ingest_official.py
.venv/bin/python scripts/build_scheme_records.py
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
.venv/bin/python scripts/evaluate_research.py
.venv/bin/python scripts/evaluate_evidence.py
```

To run the optional measured models locally, install `backend/requirements-research.txt` in the same environment and set `FORMFLOW_EMBED_MODEL=BAAI/bge-m3`. Set `FORMFLOW_RERANK_MODEL=BAAI/bge-reranker-v2-m3` to test reranking. The first run downloads multi-gigabyte weights. Models and credentials are not committed. `python scripts/evaluate_research.py` records actual model status, rank metrics and elapsed time in `data/research/evaluation.json`. Do not confuse the fast warm hybrid measurement with cold model startup. A deployment with models needs an image containing `sentence-transformers` and a writable model cache; the default Compose image only supports keyword retrieval.

For a host browser preview without Docker, migrate a temporary SQLite database, start `uvicorn app.main:app` with `PYTHONPATH=backend`, then `cd frontend && npm ci && npm run dev`. The research page is public at `http://localhost:3000`; `/api/v1/research/ask` serves cited answers. Host OCR needs Tesseract English and Kannada language data. The full Compose path was also checked with `docker compose up -d --build --wait`, `docker compose exec -T backend python -m app.smoke`, backend tests and Playwright.

## Datasets and measured results

| Dataset | Current size and status |
| --- | --- |
| Official archive | 11 fetched sources, 128 usable HTML passages; 3 PDFs archived but text excluded |
| Retrieval questions | 12 author-generated English/Kannada development probes; **0 independently reviewed** questions |
| Rule mappings | 15 source-linked draft conditions; **0 independently approved** rule versions |
| Assessment | Existing 52 synthetic fact-level demo cases; no real beneficiaries |
| Evidence optimizer | 8 author-specified synthetic development cases |
| Document extraction | Existing synthetic fixture generator only; no consented, de-identified real documents |

The 12 retrieval probes are grouped conceptually by underlying condition and have no held-out test split. They are useful for debugging, not a generalisation claim. On this machine with `sentence-transformers 5.7.0`, BGE M3 revision `5617a9f61b028005a4858fdac845db406aefb181` and bge-reranker-v2-m3 revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`, the recorded `evaluation.json` gives:

| Method | Recall@5 | MRR@10 | Measured time/query |
| --- | ---: | ---: | ---: |
| Unicode keyword | 10/12 | 0.4542 | 0.10 ms |
| BGE M3 dense | 10/12 | 0.6308 | 773.20 ms, including model setup |
| RRF hybrid | 12/12 | 0.5347 | 24.97 ms after dense setup |
| Hybrid + BGE reranker | 12/12 | 0.7069 | 540.35 ms, including reranker setup |

The deterministic answer path returned an expected citation for 11/12 development probes. That metric checks an author-specified citation ID, not semantic correctness or legal currency. The eight synthetic evidence-optimizer cases matched specified document sets and unmapped-condition flags (precision/recall 1.0 on that tiny set). The existing demo evaluation was run and copied to `data/research/demo_evaluation.json`. No measured claim about real assessment, OCR on genuine documents, source-change impact accuracy or population benefit outcomes is made. Latency is single-process local timing; the initial model download is excluded from the second run.

The full Compose smoke output recorded healthy PostgreSQL migration `001`, pgvector, Celery jobs, real Tesseract, encrypted MinIO objects, Unicode PDF export, deletion, and three monitored official source snapshots without fetch errors. Backend tests passed **122/122** inside the container. Production Chromium tests passed **9/9**, covering the three fictional verdict journeys, scanned image OCR, evidence previews, administration, Kannada report export, and English/Kannada cited research answers. These checks do not validate current government rule interpretation.

## Teacher-facing research framing

**Problem:** A welfare question may be answerable from an official page while personal eligibility still depends on a complete, current rule and credible applicant evidence. A missing document is a different state from a supported failing condition.

**Method:** Archive and hash official sources, link each proposed rule to a clause, use multilingual retrieval for discovery, apply three-valued rule logic to document-backed facts, and compute a minimum set of additional document categories for unresolved conditions. Compare old and new source versions to flag historical assessments that may need review.

**Proposed contribution:** The combination of clause provenance, unresolved-condition tracking and minimum evidence collection in this local welfare workflow is an engineering research hypothesis, not a claim of novelty or proven accuracy. Related work already studies [information sufficiency and missing evidence](https://aclanthology.org/2026.findings-eacl.217/), [complementary evidence retrieval](https://aclanthology.org/2021.eacl-main.234/), [multilingual retrieval](https://arxiv.org/abs/2402.03216), and [RAG evaluation](https://aclanthology.org/2024.eacl-demo.16/). A proper study needs independently reviewed references, held-out scheme/source-version groups, representative consented documents, error analysis and a tested change-impact benchmark.

**Limits and next work:** Independent readers must check linked government orders, currency, translations and completeness before a real rule can be activated. The OCR fact schema lacks occupation, deposits, widowhood and pension records, and the app's production security prerequisites remain incomplete. No 100-question reviewed benchmark, LLM provider, live local generation model, real-scheme assessment, or end-to-end Docker verification is claimed.
