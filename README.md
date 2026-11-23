# FormFlow AI

## Research prototype update · 23 November 2026

The project now includes an archived 11-source Karnataka government corpus, three source-linked scheme cards, English/Kannada cited question answering, optional BGE M3 hybrid retrieval and reranking, draft rule mappings, exact missing-evidence set cover, and source-change impact flags. See [the research implementation and measured results](docs/RESEARCH_PROTOTYPE.md). **Personal eligibility assessment still uses fictional demo schemes.** Real schemes require independent review of government orders, complete evidence mappings and approved rule versions before activation. The default Docker image serves keyword-backed cited guidance; optional BGE model runs were measured on the host. The full Compose stack and nine browser journeys were verified on 23 November 2026.

A locally hosted, bilingual, evidence-aware welfare discovery and preliminary assessment application for Karnataka senior citizens. **The working assessment experience uses fictional DEMO schemes. Real scheme cards and cited guidance are available for research but cannot be assessed or published in this build.** Results are not government decisions or document authentication.

The research upgrade is implemented on the `codex/research-prototype` branch. The original demonstration workflow remains available.

## Start on this computer

Open PowerShell in `C:\Users\Joyal John\Documents\ChatGPT\form flow`:

```powershell
.\scripts\start.ps1
```

The script creates `.env` with fresh random development credentials if absent, builds the images, runs migrations and seeds, starts the services, and waits for health checks. Docker Desktop must be running. First build downloads packages, OCR models and Go modules; allow several minutes. Subsequent launches use the cache.

Equivalent commands:

```powershell
.\scripts\setup.ps1
docker compose up -d --build --wait --wait-timeout 300
```

Local URLs:

| Service | URL |
| --- | --- |
| Application, citizen and caregiver journeys | http://localhost:3000 |
| Administration | http://localhost:3000 — choose Administrator in local login |
| Backend health | http://localhost:8000/health |
| API reference | http://localhost:8000/docs |
| Local object-store console | http://localhost:9001 |

Only loopback ports are published. PostgreSQL, Redis and the object-store API are internal to the Compose network. API mutations require `X-FormFlow: 1`; requests use HttpOnly, SameSite Strict session cookies. Frontend calls pass through a same-origin Next.js proxy.

## Use the demonstration

1. Open the application and choose **Find my schemes**. Use `demo.citizen` with role Citizen, or `demo.caregiver` with role Caregiver. Inventing another username creates a separate local account.
2. Request a one-time code. Enter the temporary code shown in the explicitly labeled **local development channel**. There is no fixed OTP or password. Codes expire in five minutes, are single-use and have an attempt limit. This local mechanism is intentionally unavailable outside development mode.
3. `demo.citizen` has three fictional profiles, A, B and C. Choose one. New accounts can create the same examples with the three sample buttons. Caregivers must explicitly attest authorization before creating a managed profile.
4. Read the English or Kannada notice and explicitly check the consent box. The system does not imply consent from navigation.
5. Use **Load fictional sample documents**. Actual sample PDFs go through the upload API, encrypted MinIO storage and Celery processor. Alternatively download an English or Kannada scanned PNG and upload it in the appropriate evidence category. These combined scans contain several fields; assessment uses a field only when the selected document category supports it.
6. Wait for Ready to review, inspect the document or supporting crop, and confirm unchanged fields. A correction is preserved separately and remains unverified; upload replacement evidence to support it.
7. Assess the profile. A yields LIKELY_ELIGIBLE, B yields NEEDS_EVIDENCE because income is absent, and C yields NOT_ELIGIBLE because age fails a mandatory condition. All three are fictional test results. Missing evidence is never converted into an automatic failure.
8. Inspect condition reasons, exact source-clause references, provenance, rule version and document checklist. Export the Unicode PDF report. Previous results retain their original rule versions.
9. Privacy & data supports consent withdrawal and profile deletion. Deletion removes documents, facts, confirmation history, consent and reports. Minimal action/opaque-ID audit records remain without document contents.

Language switching, high contrast and larger text are available. Read aloud uses only browser voices explicitly reported as local for the selected language. If none is available, the interface explains this and retains text. Kannada voice availability has not been verified on this computer.

## Administration

Sign out, choose Administrator at login and use an invented administrator username. Read the generated access key locally with:

```powershell
Get-Content .\data\admin-access.txt
```

Enter that key in the local admin access field, then complete the temporary-code login. The key is not included in documentation or application source. Do not expose `.env`, this key, the data folder or Docker volumes.

The admin screen supports source records on the explicit official-domain allowlist, source checks, snapshots, source-change proposals, old/new text, editable proposed JSON rules and regression fixtures, explicit approval/rejection, immutable version history, minimal audit, retention cleanup, synthetic evaluation and caseworker-label CSV import. Approval revalidates the DSL, clause resolution, scheme identity and all supplied regression cases covering the three verdicts. PostgreSQL locks prevent simultaneous conflicting publication. Old assessments show when rules have changed.

**Simulate a fictional source change** provides a reproducible local review example. No real government rule is automatically inferred or activated. Real-scheme publication is deliberately refused until complete source interpretation and independent review are implemented.

## Test and evaluate

Install host tooling for frontend/browser checks once:

```powershell
.\scripts\install.ps1
```

Run all tests against the running stack:

```powershell
.\scripts\test.ps1
.\scripts\check.ps1
.\scripts\smoke.ps1
.\scripts\evaluate.ps1
```

Individual commands:

```powershell
docker compose exec -T backend python -m pytest backend/tests -q
docker compose exec -T backend python -m ruff check backend
docker compose exec -T backend python -m app.smoke
docker compose exec -T backend python -m app.evaluation
docker compose exec -T backend python -m app.ocr_benchmark
cd frontend
npm run lint
npm test
npm run test:e2e
npm run build
```

Backend unit/integration tests use an isolated temporary SQLite database and encrypted temporary files, without changing the running PostgreSQL data. Browser tests use the actual PostgreSQL/MinIO/Redis/Celery/API stack and synthetic accounts. The live smoke script separately checks PostgreSQL migrations, pgvector availability, real OCR, encrypted object bytes, retrieval, export and object deletion. No browser API mocking is used.

Outputs:

- `data/evaluation.json`: 52 independently specified synthetic fact-level cases, verdict and condition accuracy, checklist precision/recall, incorrect positives/negatives, deduplication and citation/template validation.
- `data/ocr-evaluation.json`: actual English, Kannada and mixed-language OCR measurements on 12 synthetic raster images plus three text PDFs. A tiny fixture benchmark, not real-world OCR accuracy.
- `data/ocr-fixtures/`: the exact synthetic inputs.
- `data/live-smoke.json`: live infrastructure check results and official-source fetch status.
- `frontend/playwright-report/index.html`: latest browser report, with retained failure traces if any.
- `docs/VERIFICATION.md`: recorded final commands, outcomes and limitations.

See `docs/EVALUATION_SPEC.md` for the literal rule-test specification and human-label CSV format. Automated synthetic labels are never described as caseworker agreement.

## Operations

```powershell
.\scripts\logs.ps1        # follow this application's logs
.\scripts\stop.ps1        # stop services, preserving data
.\scripts\migrate.ps1     # apply Alembic migrations
.\scripts\seed.ps1        # idempotent fictional scheme registry seed
.\scripts\reset.ps1       # DELETE fictional accounts, profiles and uploads; preserve rule history/audit
```

Retention cleanup is scheduled hourly and source checks daily while Compose is running. Retention defaults to 30 days and applies to failed jobs too. Cleanup removes reports that contain expired evidence; it does not silently retain a personal-data copy inside historical JSON. Consent withdrawal blocks future processing and assessments, including rechecking consent before an OCR worker stores facts. It does not itself erase existing documents; use deletion for that.

Uploaded objects are Fernet-authenticated ciphertext before reaching MinIO or local disk. OCR temporary files use a RAM-backed `/tmp` in API/worker containers. Facts and consent are stored in the local relational database; whole-disk encryption and independent database backups are the operator's responsibility. Losing `.env`'s encryption key makes encrypted objects unrecoverable. SQL and object storage do not form a distributed transaction; this is a controlled local demonstration, not a certified production data system.

The MinIO public images were unavailable during implementation. `infrastructure/minio.Dockerfile` builds the pinned source release locally through Go's checksum-verified module proxy, with cached retries and no Git fallback. MinIO is AGPLv3; see its [official source-distribution documentation](https://raw.githubusercontent.com/minio/minio/RELEASE.2025-10-15T17-29-55Z/README.md). No paid service or credentials are needed to build it.

## Architecture and limits

Next.js/React/TypeScript/Tailwind frontend → FastAPI/Pydantic → SQLAlchemy/PostgreSQL 16. Alembic owns schema initialization. PostgreSQL full-text search indexes stable source clauses; pgvector is installed but the research path uses an in-process Unicode keyword index and optional dense matrix for the small archive. The default Docker image has no embedding model. Redis transports document IDs to Celery. MinIO stores encrypted document objects. Local Tesseract has `eng` and `kan`; PyMuPDF extracts embedded PDF text and shapes Kannada reports.

The pure `backend/app/rules.py` evaluator accepts only explicit facts, a validated immutable rule and an evaluation date. It has no database, network, system-clock, LLM or random dependency. Conditions support equality/inequality, ordered comparisons, membership, ranges and existence; nested AND/OR/NOT use Kleene truth tables. Provenance and reasons remain attached to each condition. Result ranking is deterministic.

Evidence extraction is deliberately conservative and currently recognizes labeled ISO dates, explicitly annual income and a limited set of English/Kannada fields. Issue dates are page-scoped; conflicting dates are not arbitrarily picked. It is not a general understanding model for every government certificate layout. Blur, brightness, resolution, denoising, contrast and limited deskew are implemented. Reliable cropping detection, perspective correction and arbitrary upside-down-page handling remain incomplete. Document classification is heuristic, not authenticated. Source-region crops can be approximate after deskew.

Malware scanning is unavailable. File signatures, parsing limits, active-PDF rejection, image limits, role/ownership checks, CSRF header/origin checks, rate limiting and local encryption are implemented. Setting `DEVELOPMENT=false` refuses startup rather than pretending an unscanned production mode is safe. Rate limiting is process-local and the supported API configuration is a single process.

Ollama, learned OCR alternatives, speech input and cloud services are not required or enabled. Optional BGE embeddings and reranking were measured on the host; the Compose default is keyword retrieval. Bilingual deterministic explanations are the working assessment path; the structured explanation validator rejects changed verdicts/thresholds/references. No external LLM integration exists. Human caseworker agreement, legal compliance, government authentication and population-level accuracy have not been established. Source fetching may fail due to remote access restrictions and records errors without bypassing them.

The archive now includes the [Vijayapura district pension page](https://vijayapura.nic.in/en/service/social-security-pensions/), [Chitradurga district scheme page](https://chitradurga.nic.in/en/scheme/ssp-en/) and Directorate scheme pages and orders. Source-linked page statements, including benefit amounts, are shown with a pending-review label; they are not approved current benefit determinations. No unsourced threshold is presented.

After the local demonstration is stable, the substantive next steps are independent review of full official scheme conditions, representative consented OCR validation, stronger certificate-layout handling, a local malware scanner, production authentication and legal/security review before real citizen data. Additional states and categories are outside this build's initial scope.

## Prerequisites and recovery

Detected here: Python 3.13, Node.js 24, Docker Desktop 29 with a functioning Linux engine. Native Tesseract is absent; the Docker image provides both language models. If prerequisites are missing on another Windows machine:

```powershell
winget install -e --id Docker.DockerDesktop
winget install -e --id Python.Python.3.13
winget install -e --id OpenJS.NodeJS.LTS
```

Docker Desktop/WSL installation can require administrator access or a restart. Launch Docker Desktop and wait for its Linux engine before running the start script. Host Python/Node are only needed for source-level development and host frontend tests; Docker supplies runtime dependencies.

If an image/module download fails, rerun `docker compose build` and then the start command; caches preserve completed downloads. Do not replace unavailable upstream images with arbitrary mirrors. If ports 3000, 8000 or 9001 conflict, stop the conflicting process or deliberately change the loopback port mappings and corresponding origin/URL configuration together. Inspect `docker compose ps` and `docker compose logs --tail 100` for the actual failing service. Do not reset or remove volumes to troubleshoot a routine startup failure.
