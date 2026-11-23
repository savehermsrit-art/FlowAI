# Independently specified synthetic decisions

These rules are fictional test rules, not Karnataka government requirements. The human-written test specification is:

- Age at assessment date is at least 60 years, including exactly 60.
- State is Karnataka (case-insensitive).
- Annual income is no greater than INR 50,000, including exactly 50,000.
- Income evidence must have an issue date within 366 days; expired documents are insufficient.
- Each field requires supporting evidence of the correct document category, confidence at least 0.75 and user confirmation.
- A corrected, unconfirmed, unreadable, missing or conflicting field is insufficient evidence.
- One false mandatory condition makes the combined result NOT_ELIGIBLE even when another condition is unknown.
- With no false condition, an unknown condition means NEEDS_EVIDENCE. All true means LIKELY_ELIGIBLE.

The 13 cases explicitly label eligible, exact age boundary, exact income boundary, under-age, over-income, other-state, missing-income, no-evidence, conflict, unconfirmed, corrected, low-confidence and expired. They are repeated across four named strata, totaling 52 fact-level cases. Strata names are not OCR benchmark results. Expected labels are literal test data and never produced by calling the evaluator. This specification is author-reviewed; **independent caseworker review has not occurred**.

`python -m app.evaluation` saves actual condition, verdict, checklist and explanation-validation results to `data/evaluation.json`. `python -m app.ocr_benchmark` separately runs Tesseract on real synthetic raster fixtures and saves measurements, missing fields and failures to `data/ocr-evaluation.json`. English/Kannada/mixed text are physically present in those images.

The administration page imports independently labeled CSV rows with columns `id,verdict`. IDs are listed in the fact-level evaluation JSON. No claim of human agreement is made until someone supplies actual human labels. The test CSV used by automated integration tests is synthetic, not a human evaluation.

Source monitoring tests classify fixture changes. Approval tests validate a complete rule and execute supplied regression cases covering all three verdicts before activation. These tests demonstrate the control mechanism, not that a government rule is substantively complete.
