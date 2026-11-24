# FormFlow AI implementation record

Research update, 23 November 2026: see [docs/RESEARCH_PROTOTYPE.md](docs/RESEARCH_PROTOTYPE.md) for the archived official corpus, source-linked Q&A, optional measured BGE retrieval, synthetic evidence guidance and current blockers. The record below describes the earlier fictional-demo milestone and its then-current environment.

RAG update, 24 November 2026: the research Q&A now sends retrieved official passages to a local Ollama model for English/Kannada answer generation. It checks returned source IDs, exact supporting quotes and numeric claims. The separate fictional eligibility evaluator remains deterministic.

Last verified: 17 November 2026 (Asia/Kolkata).

## Current status

**Functional local DEMO, running in Docker Compose. Extended specification partially complete.** All assessment rules are explicitly fictional. Real schemes are discovery references only. No Git commands, repository setup, pushes or cloud deployment performed; the existing .git directory was left alone.

## Implemented stages

1. **Environment/infrastructure:** Python 3.13, Node 24 and Docker inspected. Seven services built and health checked: PostgreSQL/pgvector, Redis, locally source-built MinIO, FastAPI, Celery worker/scheduler and production Next.js. Local secrets, dependency locks, Alembic migration and PowerShell scripts supplied. Native Tesseract absent; Docker includes English/Kannada models.
2. **Deterministic core:** strict JSON DSL, all comparison operators, Kleene logic/nesting, dates, conservative missing/conflicting/expired/corrected evidence, provenance, stable ranking and deduplicated checklists. Literal independent synthetic specification and 52-case evaluation.
3. **Accounts/profiles/consent:** temporary development codes, secure session cookies, roles, caregiver attestation and ownership isolation. Versioned explicit consent. Three reusable fictional citizen profiles seeded without consent.
4. **Documents:** content validation, size/page/raster limits and active-PDF rejection; encrypted storage; queued jobs; PDF extraction and local Tesseract; quality checks, denoising/contrast and limited deskew. Original/normalized values, page-scoped issue dates, review/correction history, document/page/region previews.
5. **Registry/retrieval:** two fictional assessable schemes and two official discovery references unavailable for assessment. Local snapshots, hashes, stable clause IDs, language detection and PostgreSQL full-text search. pgvector installed without embeddings.
6. **Citizen frontend:** responsive bilingual landing/login/profile/consent/upload/status/review/results/checklist/report/history/privacy. All primary actions call backend APIs. All three demonstration verdicts verified.
7. **Caregiver/accessibility:** multiple owned profiles, explicit attestation, keyboard controls, visible focus, high contrast/larger text, Kannada mobile layout, local-voice detection/text fallback. Representative Axe checks and modal keyboard dismissal verified.
8. **Explanations:** deterministic bilingual reasons and Unicode PDFs. Strict structured explanation validator. No LLM dependency.
9. **Administration:** allowlisted official sources, daily monitoring, local snapshots and clause indexing, change classification, editable proposed rules/tests, explicit approval/rejection, required schema/clause/regression checks, locked atomic version publication, historical results and minimal audits. Both official fetches succeeded. Real-rule publication disabled.
10. **Security/evaluation:** consent/ownership/CSRF/origin checks, strict cookies, process-local rate limits, encrypted uploads and RAM OCR scratch. Retention cleanup includes failed jobs and embedded reports; deletion removes associated objects/data. Non-development operation refused without scanner/security prerequisites. Human-label import exists; no human evaluation claimed.
11. **Final integration:** all seven containers healthy; production-browser journeys in both languages, real OCR, retrieval, exports, physical object deletion and administration verified.

## Actual checks

- Backend: **116 passed**, Windows and Linux. Two upstream deprecation warnings; no failures.
- Frontend: **6 passed**. Ruff, TypeScript and Prettier passed.
- Browser: **7 passed**, production containers, no API mocking; includes three verdicts, real image OCR, previews, authorization, admin approval/rejection, Kannada and exports.
- Golden evaluation: **52/52 verdicts, 156/156 condition statuses**, checklist precision/recall 1.0, no incorrect positive/negative or duplicate requests on this dataset.
- OCR: **12 raster fixtures + 3 text PDFs**, zero processing failures. Normalized fields: English 11/12, Kannada 12/12, mixed 11/12. Small fixture measurements only.
- Live smoke: PostgreSQL migration 001, pgvector, queue/worker, OCR, encrypted MinIO bytes, retrieval, Kannada PDF, deletion/object removal passed. Both official sources snapshotted without fetch errors.
- Final Kannada export rendered; both pages visually inspected.

Evidence: `docs/VERIFICATION.md`, `data/verification-tests.log`, `data/verification-checks.log`, `data/live-smoke.json`, `data/evaluation.json`, `data/ocr-evaluation.json`, `frontend/playwright-report/index.html`.

## Remaining scope

- **Unavailable:** complete current real-government rules and substantive independent approval. No real amounts, thresholds, deadlines or application instructions invented.
- **Incomplete:** general certificate-layout understanding; reliable crop/perspective/arbitrary-rotation handling; malware scanner and production authentication/readiness. Extraction requires recognized labels, explicit annual income and ISO dates.
- **Optional, absent:** embeddings, local Ollama provider, alternative OCR and speech input.
- **Unverified:** Kannada local voice, representative real-document OCR, caseworker agreement and formal accessibility/legal certification.

## Resume

Read README and this record. Start with `scripts/start.ps1`; do not reset for routine startup. Preserve working modules. Real-scheme work needs complete official clauses and independent substantive review before changing publication restrictions. Next engineering work: broader labeled-document/layout validation, local malware scanning and stronger non-development authentication.
