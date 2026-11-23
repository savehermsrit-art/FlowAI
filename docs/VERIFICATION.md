# Verification record

Implementation date: 17 November 2026 (Asia/Kolkata). Final verification ran against the production Next.js image and local Compose services, using fictional data only.

## Confirmed so far

- Windows and Linux-container backend suites: **116 tests passed**. Final container run: 116 passed in 2.72 seconds. Two upstream deprecation warnings (test-client httpx adapter and the tests' fitz import alias); no failures.
- Frontend: 6 Vitest/React Testing Library tests passed; strict TypeScript checks passed.
- Browser integration: **7 Playwright tests passed in 43.2 seconds**, production frontend, actual API, PostgreSQL, Redis, Celery and encrypted MinIO objects. All three verdicts, caregiver isolation, admin approval/rejection, English/Kannada journeys, rendered document previews, keyboard modal dismissal and report downloads exercised.
- Axe checks on landing and result pages passed. Kannada mobile viewport at 390px had no horizontal overflow. These checks are not a complete WCAG certification or usability study.
- Kannada report pages were rendered and visually inspected; no missing-glyph blocks observed. Schemes start on separate pages with page numbering.
- OCR: 12 scanned synthetic fixtures, zero processing failures. Normalized field accuracy: English 11/12; Kannada 12/12; mixed 11/12. Raw exact match differs for Kannada state names because normalization maps ಕರ್ನಾಟಕ to Karnataka. Three document-specific text PDFs also passed their expected field checks.
- Pure engine evaluation: 52/52 scheme verdicts and 156/156 condition statuses agreed with literal synthetic specification; checklist precision/recall 1.0; zero incorrect positives, incorrect negatives or duplicate requests in this dataset. No caseworker evaluation has occurred.
- Final `docker compose up -d --build --wait --wait-timeout 180` exited successfully. **All seven services healthy:** frontend, API, PostgreSQL, Redis, MinIO, Celery worker and scheduler. Production frontend build passed.
- Live smoke passed: consent blocking, queued processing, real Tesseract, positive assessment, supporting crop, Kannada PDF, PostgreSQL full-text retrieval, encrypted MinIO bytes, Alembic revision 001, pgvector, profile deletion and physical object removal.
- Both official discovery pages fetched successfully: one local snapshot each, no fetch error. Public source bytes remain under `data/official-sources/`. This does not validate complete government eligibility rules.
- SQL confirmed fictional profiles A, B and C exist for `demo.citizen`, without implied consent. Browser tests did not modify these profiles.
- Python Ruff, strict TypeScript and Prettier checks passed. Frontend npm audit reported zero vulnerabilities during installation; this is not a full security audit.

## Reproduction and logs

With services running: `scripts/test.ps1`, `scripts/check.ps1`, `scripts/smoke.ps1`, `scripts/evaluate.ps1`, and `docker compose ps`.

Saved output: `data/verification-tests.log`, `data/verification-checks.log`, `data/evaluation.json`, `data/ocr-evaluation.json`, `data/live-smoke.json`, and `frontend/playwright-report/index.html`. Final Kannada export pages `data/final-report-page-1.png` and `data/final-report-page-2.png` were both visually inspected. Fixtures contain fictional data only.

## Scope classification

| Area | State |
| --- | --- |
| Local DEMO citizen and caregiver journey | Implemented; browser verified |
| English and Kannada primary screens and PDFs | Implemented; browser and visual verification |
| Database migrations, object storage, broker, worker and scheduler | Running and healthy; live smoke verified |
| Deterministic DSL, three-valued logic, provenance, ranking | Implemented; unit/golden verified |
| Consent, ownership, session security, deletion and retention | Implemented; automated checks |
| Admin review, fictional rule approval, historical versions | Implemented; integration/browser verified |
| Source snapshots, allowlist, clause indexing, monitoring | Implemented; fixtures verified; remote fetch status recorded separately |
| Real government-scheme assessment/publication | Unavailable; requires complete official-rule interpretation and independent approval |
| General certificate-layout extraction and robust perspective/rotation/crop detection | Incomplete; current heuristics documented |
| Malware scanning and non-development authentication | Incomplete; non-development startup blocked |
| Local voice availability for Kannada | Unverified; runtime local-only detection and text fallback |
| Embeddings, Ollama, alternative OCR engines, speech input | Optional, not implemented/enabled |
| Caseworker agreement, formal legal compliance, population-level OCR accuracy | Not established |

The overall specification is **partially complete**; the local DEMO is functional. Do not present this as ready for real citizen data or official eligibility decisions.
