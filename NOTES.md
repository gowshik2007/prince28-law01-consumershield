# ConsumerShield — Development Notes

This file records implementation work, verification results, and deployment evidence from Day 1 onward.

## Day 1 — Project foundation and FastAPI skeleton

### Project setup

- Initialized the Python project using `uv`.
- Created the `src` layout for the ConsumerShield package.
- Added Python version configuration and dependency lockfile.
- Added the initial project README.

### Project planning

- Added the project card and initial project description.
- Documented functional and non-functional requirements in `docs/REQUIREMENTS.md`.
- Created 10 real-user evaluation questions in `docs/QUESTIONS.md`.
- Identified the initial evaluation scenario: an engineering student in Chennai whose Rs 45,000 laptop arrived damaged.

### Code quality and security

- Added Ruff for linting and formatting.
- Configured pre-commit hooks.
- Added secret scanning.
- Created `.env.example`.
- Added `.gitignore` rules for local configuration and generated files.

### FastAPI foundation

- Created the FastAPI application structure.
- Added application configuration using Pydantic Settings.
- Added structured logging.
- Implemented health and document routes.
- Added request middleware and centralized error handling.
- Added initial sample records in `data/sample_records.json`.

### API tests

- Added tests for health and readiness endpoints.
- Added document endpoint tests.
- Added error-handling tests.
- Added fail-fast configuration tests.

### Result

- Python project initialized with a `src` layout.
- Initial FastAPI application implemented.
- Sample data added.
- Quality checks and secret scanning configured.
- Initial API test coverage established.

## Day 2 — Database migrations

### Migration history

```text
5ce2b0a92557 -> 13e79d5f23f5 (head), add GIN index on metadata
<base> -> 5ce2b0a92557, create documents and pages
```

### Verification

- Migration 1: Created `documents` and `pages` tables.
- Migration 2: Added GIN index on `documents.metadata`.
- Downgrade -1: Successful.
- Alembic current revision recorded during intermediate verification: `5ce2b0a92557`.
- Upgrade head: Successful.
- Alembic history: Both migrations verified.

## Day 3 — PostgreSQL and idempotent loader

### Loader verification

First load:

```text
records=5 inserted=5 updated=0 unchanged=0
```

Second load (idempotency):

```text
records=5 inserted=0 updated=0 unchanged=5
```

Modified one record (update detection):

```text
records=5 inserted=0 updated=1 unchanged=4
```

Restored original record:

```text
records=5 inserted=0 updated=1 unchanged=4
```

### Result

- Five JSON records loaded into PostgreSQL.
- Repeated loading created no duplicates.
- SHA-256 fingerprints detected modified records.
- Original data restored successfully.
- All database operations run inside one transaction.

## Day 4 — Docker, Compose and tests

### Docker image

```text
docker run --rm consumershield:dev id
uid=999(app) gid=999(app)
```

### Docker image verification

- Multi-stage Docker build completed successfully.
- Runtime uses a non-root `app` user.
- Image disk usage: approximately 300 MB.
- Image content size: approximately 70 MB.

### Docker Compose

- PostgreSQL with pgvector.
- Redis service.
- API service.
- Database migrations run before API startup.
- Sample-data loader runs as part of the migration service.
- Health checks and service dependencies configured.
- `/health` returns HTTP 200 when the API is running.
- `/ready` returns HTTP 503 when the database is unavailable.
- `/ready` returns HTTP 200 after the database is restored.

### Tests and coverage

- Unit tests: 16 passed.
- Integration tests: 7 passed.
- Combined test coverage: 92%.
- Unit-only coverage: 85%.
- Integration tests use a separate test database.

### Developer workflow

- Makefile added for common development tasks.
- Poe tasks added for Windows-compatible commands.
- README includes local startup and testing instructions.

### Result

- Docker image builds successfully.
- Application runs as a non-root user.
- Compose starts the API, PostgreSQL and Redis services.
- Database readiness is verified.
- Unit and integration test suites pass.

## Day 5 — Live deployment, monitoring and rollback

### Production

- Live URL: https://consumershield-82yz.onrender.com
- CI run (PR #4): https://github.com/gowshik2007/prince28-law01-consumershield/actions/runs/44699995646
- Automatic CD run (PR #5): https://github.com/gowshik2007/prince28-law01-consumershield/actions/runs/44706349278
- PR #5 merged: 2026-11-20 08:53:35 UTC.
- Automatic deployment completed: 2026-11-20 08:55:58 UTC.
- Merge-to-live time: 2 minutes 23 seconds.
- Automatic deployment duration: 52 seconds.

### Production smoke test

```text
ok /health -> 200, git_sha 4d7fdbb0569f7254fe62a8500ba7280aad8cfa94
ok /ready -> 200, database True
ok /v1/documents?limit=1 -> 200
Smoke test passed
```

### Rollback drill

- Rollback target SHA: `cf9ed7ee0a78545b9de8ba8acaf9732e9c3f925e`
- Rollback run: https://github.com/gowshik2007/prince28-law01-consumershield/actions/runs/44708462362
- Rollback duration: 44 seconds.
- Rollback smoke test: all three endpoints passed.
- Roll-forward SHA: `4d7fdbb0569f7254fe62a8500ba7280aad8cfa94`
- Roll-forward run: https://github.com/gowshik2007/prince28-law01-consumershield/actions/runs/44708765238
- Roll-forward duration: 53 seconds.
- Roll-forward smoke test: all three endpoints passed.
- Final production health endpoint confirmed the roll-forward SHA.

### Database safety

- Rollback deployed an older application image without running migrations.
- The database schema was not downgraded, and existing data was preserved.
- The older application remained compatible with the current schema, confirmed by successful readiness and document API smoke tests.

### Secrets and configuration

- GitHub Actions configuration entries: `RENDER_DEPLOY_HOOK` and `DATABASE_URL`.
- GitHub Actions variable: `LIVE_URL`.
- Render environment variables: `APP_ENV` and `DATABASE_URL`.

### Monitoring

- UptimeRobot monitors https://consumershield-82yz.onrender.com/health.
- Check interval: 5 minutes.
- Email alerts enabled.
- Monitor-specific API key used for the public README uptime badge.
- HEAD support added to `/health` because UptimeRobot uses HEAD requests. The fix was merged and deployed through PR #6.

### Cold start improvement

- Render free services can spin down after inactivity.
- An always-on paid instance avoids free-instance spin-down and reduces cold starts.

## Day 6 — EXPLAIN and GIN index

### Query used

```text
python -m uv run python scripts/explain.py product_category "E-commerce goods and services"
```

### EXPLAIN output — Normal planner

```text
Seq Scan on documents (cost=0.00..11.00 rows=1 width=36) (actual time=0.814..0.817 rows=1.00 loops=1)
Filter: (metadata @> '{"product_category": "E-commerce goods and services"}'::jsonb)
Rows Removed by Filter: 4
Execution Time: 0.846 ms
```

### EXPLAIN output — Sequential scan disabled

```text
Bitmap Heap Scan on documents (cost=12.81..16.82 rows=1 width=36) (actual time=2.038..2.039 rows=1.00 loops=1)
Recheck Cond: (metadata @> '{"product_category": "E-commerce goods and services"}'::jsonb)
Heap Blocks: exact=1
-> Bitmap Index Scan on ix_documents_metadata_gin (cost=0.00..12.81 rows=1 width=0) (actual time=2.001..2.001 rows=1.00 loops=1)
Index Cond: (metadata @> '{"product_category": "E-commerce goods and services"}'::jsonb)
Execution Time: 2.088 ms
```

### Why did the planner choose a Seq Scan?

The table currently contains only five records. Scanning all records is cheaper than using an index.

### When would it switch to the GIN index?

When the table grows and PostgreSQL estimates that an index scan will be more efficient than a sequential scan.

### Result

- Verified the normal query planner.
- Confirmed the GIN index is usable.
- Verified JSONB metadata filtering.
- Observed that the sequential scan was faster for the small five-record dataset.

## Final deployment verification — November 20, 2026

### Latest deployment

- Latest successful main CD run: https://github.com/gowshik2007/prince28-law01-consumershield/actions/runs/44713447660
- Final deployed Git SHA: `ce50414c457658f9bfb59e12bd6bc78a1344457c`
- Production `/health`: HTTP 200.
- Production `/health` HEAD request: HTTP 200.
- The health response reports the final deployed Git SHA.
- The `/health` HEAD fix from PR #6 is deployed.

### Final status

- CI/CD pipeline verified.
- Automatic Render deployment verified.
- Production health endpoint verified.
- UptimeRobot-compatible HEAD health check verified.
- Rollback and roll-forward drill completed.
- Production deployment reports the expected Git SHA.

## Day 6 — Corpus downloader and dataset verification

### Downloader implementation

- Downloader CLI: `scripts/fetch.py`.
- Download implementation: `src/consumershield/ingest/fetch.py`.
- Unit tests: 17 passed.
- Full Ruff checks passed.
- Full project test suite: 35 passed, 7 skipped.
- Redirect destinations are checked against robots.txt.
- Raw downloaded files are excluded from Git.
- Pre-commit checks passed, including secret scanning.

### Registered dataset

- Dataset: Open India Law — Central Indian Legislation Dataset.
- Format: Parquet.
- Source URL: https://oss-data-in.vaquill.ai/v2026.08.1/in_central_legislation.parquet
- Dataset licence recorded in source register: CC BY 4.0.
- Original legal text source URLs are retained in the processed records.
- Downloaded file size: 26,515,484 bytes.
- SHA-256 checksum recorded in `data/manifest.jsonl`:
  `2a3aab1a2d7a8d3f2e87035870ff6f2f429d34d60b98dd6ab389502df0d4cb73`

### Download verification

Initial download:

```text
[downloaded] 26,515,484 bytes
sources=1 downloaded=1 skipped=0 blocked=0 failed=0 seconds=3.4
```

Repeat run:

```text
sources=1 downloaded=0 skipped=1 blocked=0 failed=0 seconds=0.3
```

### Corpus extraction

- Source dataset records: 74,484.
- Extracted records matching `The Consumer Protection Act, 2019`: 156.
- Processed output: `data/processed/consumer_protection_act_2019.jsonl`.
- Processed JSONL size: 207,129 bytes.
- Extracted characters: 206,619.
- Estimated tokens: 51,655.
- Estimated chunks at 800 tokens with 100-token overlap: 74.
- Text encoding verification: zero replacement characters and zero detected mojibake sequences.

### Dataset report

- `DATASET.md` generated with source and licence information.
- Known gaps documented.
- Processed JSONL is included in the corpus inventory.
- Parquet extraction limitations are documented.
- Estimated embedding storage: 0.43 MiB.
- Estimated embedding cost: $0.001033 using the report's assumed price of $0.0200 per million tokens.
- These are planning estimates, not measured embedding usage or billing.

### Git and repository safety

- `data/manifest.jsonl` committed.
- `data/sources.csv` committed with dataset licence information.
- Processed Consumer Protection Act JSONL committed.
- Raw downloaded Parquet files remain ignored by Git.
- `pyarrow` added to project dependencies.
- Secret scanner baseline added for the reviewed public SHA-256 checksum.

### Pull request and CI

- PR #15: Add Consumer Protection Act corpus.
- PR URL: https://github.com/gowshik2007/prince28-law01-consumershield/pull/15
- PR merged successfully using squash merge.
- CI build image: passed.
- CI lint and test: passed.
- Local pre-commit: all hooks passed.

### Current measured downloader status

```text
sources=1 downloaded=0 skipped=1 blocked=0 failed=0 seconds=0.3
```

### Recovery verification and remaining limitation

- Re-running the downloader confirmed that an already completed download is skipped rather than downloaded again.
- This verifies repeat-run/idempotent skip behaviour.
- A real interrupted transfer was tested using a local HTTP server. The active download was cancelled after 524,288 bytes; the partial file was preserved.
- The next request resumed at byte 524,288 and received HTTP 206 Partial Content.
- Final file size: 8,388,608 bytes. SHA-256 matched the expected complete payload.
- This verifies actual socket interruption and byte-range resume locally; an external-source interruption has not been tested.

### Remaining work

- Record measured download and processing capacity in `docs/CAPACITY.md`.
- Answer the four capacity-planning questions in `docs/CAPACITY.md`.
- If partial-download recovery is a strict requirement, perform and document a separate interruption test.

## Day 6 — verified update (23 November 2026)

- Processed 96 unique CCPA order-listing metadata records into `data/processed/ccpa_orders_metadata.jsonl`.
- Original CCPA metadata remains preserved under `data/raw/ccpa-orders/`.
- These records are listing metadata only; full order documents were not downloaded.
- CCPA licence status remains unverified.
- Dataset report regenerated: 875,445 extracted characters, approximately 218,862 tokens, and 313 estimated chunks.
- Validation: 36 tests passed; Ruff lint passed; 45 files passed formatting check.
- Remaining: 4 more CCPA listing records to reach 100, full order documents subject to permission, and the outstanding rules/guidelines corpus.

### Actual interruption and resume test (23 November 2026)

- Test method: active HTTP download interrupted by cancelling the running download task.
- Bytes preserved at interruption: 524,288.
- Resume request started at byte: 524,288.
- Resume response: HTTP 206 Partial Content.
- Final file size: 8,388,608 bytes.
- SHA-256: matched the expected complete payload.
- Result: PASSED using a local HTTP test server. No production corpus files were changed.

## Day 7 — Document parsing and first corpus batch

### Parser implementation

- Added PDF parsing using PyMuPDF and pypdf.
- Added HTML parsing using Trafilatura.
- Added text and structured-data parsing, including JSONL.
- Added text cleaning, repeated-line removal, page splitting and heading extraction.
- Added database storage for parsed documents, pages and parse failures.
- Added `scripts/parse_corpus.py` to generate and parse documents from the Open India Law Parquet dataset.

### First batch verification

- Source dataset: 74,484 legal-section records.
- Distinct Acts in dataset: 1,568.
- Generated legal documents: 20.
- Successfully parsed and stored: 20.
- Failed documents: 0.
- Total parsed pages: 6,455.
- Total runtime: 25.5 seconds.
- Neon database verification: 20 documents returned.
- Page-content verification: 5 pages inspected.
- Parser recorded as `plain` for all 20 generated Markdown documents.

### Observation

- Parsed page text contains meaningful legal content and section information.
- Page headings can retain a previous section heading when a page continues into another section. For example, the inspected Motor Vehicles Act page 157 contains content from Sections 215 and 216 while its stored heading path starts at Section 215.
- This is a heading-continuity limitation to investigate during further parser improvements.

### Result

- First 20 derived legal documents successfully parsed and stored in Neon.
- Document metadata and page records verified using SQL.
- No parse failures in the first batch.

## Day 7 - Part 4: Full corpus parsing and failure verification

### Full corpus parsing

- Source dataset: Open India Law Parquet dataset.
- Total source records: 74,484 legal-section records.
- Distinct Acts: 1,568.
- Generated Markdown documents: 1,568.
- Newly parsed documents: 1,548.
- Previously parsed documents: 20.
- Total documents parsed and stored: 1,568.
- Pages reported by first parser run: 22,772.
- First run duration: 697.7 seconds.
- Second run: 0 newly parsed, 1,568 already parsed, 0 failures, 0 new pages.
- Second run duration: 27.6 seconds.

### Failure verification

- Neon parse_failures table: 0 rows.
- Failure groups by reason: none.
- Retry was unnecessary because no failures were recorded.

### Neon database verification

- Parsed documents: 1,568.
- Total pages recorded in document metadata: 29,227.
- Actual stored page rows: 29,227.
- Document metadata page total matches the pages table count.

### Result and limitation

- All 1,568 available Acts were generated, parsed and stored.
- Re-running the parser confirmed that already-parsed documents are skipped.
- No parse failures were recorded.
- This available Parquet corpus contains 1,568 Acts; it is not the separate 364-file HTML/Markdown/PDF corpus mentioned in the original exercise.

## Day 7 - Part 5: Parser comparison

| File | Format | Parser A | Parser B | A pages | B pages | A chars | B chars | A tables | B tables | A time (s) | B time (s) | Review / result |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| data/raw/007-Document_Parsing_PDFs_HTML_Tables_OCR.pdf | .pdf | PyMuPDF | pypdf | 13 | 13 | 15432 | 14850 | 12 | 2 | 2.578 | 0.313 | PyMuPDF extracted more characters; inspect quality |
| data/raw/department-of-consumer-affairs/e-commerce-rules-1732703966-4db15cc1.pdf | .pdf | PyMuPDF | pypdf | 11 | 11 | 36222 | 35818 | 0 | 0 | 1.591 | 1.326 | PyMuPDF extracted more characters; inspect quality |
| data/raw/department-of-consumer-affairs/cp-act-2019-1732700731-e507b033.pdf | .pdf | PyMuPDF | pypdf | 40 | 40 | 127405 | 127785 | 0 | 0 | 0.563 | 0.778 | Both parsers extract almost identical readable legal content, including headings and Section 1. PyMuPDF has slightly cleaner line formatting and is faster (0.563s vs 0.778s); pypdf extracts 380 more characters, with no meaningful quality advantage. |
| data/raw/central-consumer-protection-authority/ccpa-notification-1732707665-3103f017.pdf | .pdf | PyMuPDF | pypdf | 11 | 11 | 37013 | 36485 | 0 | 0 | 1.134 | 1.309 | PyMuPDF extracted more characters; inspect quality |
| data/raw/sample-scanned.pdf | .pdf | PyMuPDF | pypdf | 0 | 0 | 0 | 0 | 0 | 0 | 0.038 | 0.004 | One or both parsers failed; inspect errors |
| data/processed/capacity_test_corpus.pdf | .pdf | PyMuPDF | pypdf | 106 | 106 | 430983 | 426913 | 0 | 0 | 0.951 | 1.796 | PyMuPDF extracted more characters; inspect quality |
| data/raw/Fitness Journal.html | .html | Trafilatura | Plain tag-stripping | 1 | 1 | 383 | 1337 | 0 | 0 | 0.040 | 0.007 | Plain tag-stripping extracted more characters; inspect quality |
| data/raw/sample-table-no-gridlines.pdf | .pdf | PyMuPDF | pypdf | 1 | 1 | 555 | 539 | 0 | 0 | 0.025 | 0.017 | PyMuPDF extracted more characters; inspect quality |
| data/raw/sample-multipage.pdf | .pdf | PyMuPDF | pypdf | 10 | 10 | 7096 | 6811 | 0 | 0 | 0.075 | 0.126 | PyMuPDF extracted more characters; inspect quality |
| data/raw/sample-scanned-table.pdf | .pdf | PyMuPDF | pypdf | 0 | 0 | 0 | 0 | 0 | 0 | 0.050 | 0.002 | One or both parsers failed; inspect errors |

### D07 · Parsing my corpus

- Files in the manifest: 1,568 generated legal documents · parsed: 1,568 · failed: 0 · pages in Postgres: 29,227
- Parsing coverage: 100% of generated documents

### Failures by reason

| Reason | Files | What I did |
|---|---:|---|
| No failures recorded | 0 | No retry or fix was required |

- The one I fixed: None — no failed files were recorded, so a failed-file fix was not required.

### What I saw when I read my parsed pages

- A page where the heading path is right (document, page, path): A page with heading metadata was confirmed during the earlier Neon inspection, but the exact document, page number and full heading path still need to be recorded.
- Something that came out wrong (document, page, what): Motor Vehicles Act, page 157 — content from Sections 215 and 216 appears on the page, while the stored heading path starts at Section 215.
- A table: The Customs Tariff Act, 1975 has 601 extracted tables. Whether the stored output is a proper Markdown grid or loose text still needs manual verification.

### My parser choice

- For PDFs I use PyMuPDF because it extracted 12 tables compared with pypdf's 2 in the table-heavy test PDF. In the Consumer Protection Act comparison, PyMuPDF took 0.563 seconds compared with pypdf's 0.778 seconds. The inspected text was almost identical, with slightly cleaner line formatting from PyMuPDF.
- A kind of document in my corpus that neither parser handles well: Scanned PDFs without an OCR text layer. Both parsers returned zero extracted characters for the scanned test PDFs.

### One thing that went wrong today, and how I fixed it

- The integration tests initially failed because Docker was not running and PostgreSQL was unavailable. I started Docker Desktop, brought up the Docker Compose services and reran the integration tests successfully.

### Manual inspection

- Inspected three stored legal documents in Neon: The Companies Act, 2013; The Customs Tariff Act, 1975; and The Income-tax Act, 1961.
- All three documents contained meaningful extracted text. Page 2 had heading metadata; page 1 had an empty heading array.
- Companies Act: 546 pages, 93 tables and 1,573,723 characters.
- Customs Tariff Act: 712 pages, 601 tables and 1,803,883 characters.
- Income-tax Act: 1,288 pages, 20 tables and 3,692,599 characters.

### Parser comparison observations

- `data/raw/007-Document_Parsing_PDFs_HTML_Tables_OCR.pdf`: PyMuPDF extracted 15432 characters and 12 tables in 2.578s; pypdf extracted 14850 characters and 2 tables in 0.313s. Character counts alone do not establish extraction quality; inspect the actual content.
- `data/raw/department-of-consumer-affairs/e-commerce-rules-1732703966-4db15cc1.pdf`: PyMuPDF extracted 36222 characters and 0 tables in 1.591s; pypdf extracted 35818 characters and 0 tables in 1.326s. Character counts alone do not establish extraction quality; inspect the actual content.
- `data/raw/department-of-consumer-affairs/cp-act-2019-1732700731-e507b033.pdf`: Both parsers extracted almost identical readable legal content, including the Act title, Chapter I and Section 1. PyMuPDF extracted 127405 characters in 0.563s; pypdf extracted 127785 characters in 0.778s. PyMuPDF had slightly cleaner line formatting and was faster. The additional 380 characters from pypdf did not demonstrate a meaningful quality advantage.
- `data/raw/central-consumer-protection-authority/ccpa-notification-1732707665-3103f017.pdf`: PyMuPDF extracted 37013 characters and 0 tables in 1.134s; pypdf extracted 36485 characters and 0 tables in 1.309s. Character counts alone do not establish extraction quality; inspect the actual content.
- `data/raw/sample-scanned.pdf`: PyMuPDF extracted 0 characters and 0 tables in 0.038s; pypdf extracted 0 characters and 0 tables in 0.004s. Character counts alone do not establish extraction quality; inspect the actual content.
- `data/processed/capacity_test_corpus.pdf`: PyMuPDF extracted 430983 characters and 0 tables in 0.951s; pypdf extracted 426913 characters and 0 tables in 1.796s. Character counts alone do not establish extraction quality; inspect the actual content.
- `data/raw/Fitness Journal.html`: Trafilatura extracted 383 characters and 0 tables in 0.040s; Plain tag-stripping extracted 1337 characters and 0 tables in 0.007s. Character counts alone do not establish extraction quality; inspect the actual content.
- `data/raw/sample-table-no-gridlines.pdf`: PyMuPDF extracted 555 characters and 0 tables in 0.025s; pypdf extracted 539 characters and 0 tables in 0.017s. Character counts alone do not establish extraction quality; inspect the actual content.
- `data/raw/sample-multipage.pdf`: PyMuPDF extracted 7096 characters and 0 tables in 0.075s; pypdf extracted 6811 characters and 0 tables in 0.126s. Character counts alone do not establish extraction quality; inspect the actual content.
- `data/raw/sample-scanned-table.pdf`: PyMuPDF extracted 0 characters and 0 tables in 0.050s; pypdf extracted 0 characters and 0 tables in 0.002s. Character counts alone do not establish extraction quality; inspect the actual content.

### Corpus limitation

- Available PDF files in data/: 12.
- Available HTML files in data/: 1.
- Files compared in this run: 10.
- HTML parser comparison has been tested using Fitness Journal.html.

- The ten-file comparison requirement is complete: 9 PDFs and 1 HTML file were compared.
- The original separate 364-file corpus was not available; public sample PDFs were used to complete the ten-file comparison.


## D07 - Parsing my corpus

### D07 - Parsing my corpus

- Files in the manifest: 1,569 (including 1 source Parquet dataset) - parsed: 1,568 - failed: 0 - pages in Postgres: 29,227.
- Parsing coverage: 100% of 1,568 individual Act documents (excluding the source Parquet entry).

### Failures by reason

| Reason | Files | What I did |
|---|---:|---|
| None | 0 | No parse failures were recorded; no retry or fix was required. |

- The one I fixed: None. No individual file failure was recorded.

### What I saw when I read my parsed pages

- A page where the heading path is right: Abkari, Bengal Act, 1840, page 2, Section XI.
- Something that came out wrong: Abkari, Calcutta, 1849, page 2 contains Sections IV and IX, but the heading path identifies only Section IV.
- A table: The Customs Tariff Act, 1975, page 1. The extracted content uses loose text with pipe separators, not a Markdown grid.

### My parser choice

- For PDFs I use PyMuPDF because the 007 sample PDF produced 15,432 characters and 12 tables, compared with pypdf's 14,850 characters and 2 tables.
- PyMuPDF extracted more table content in that comparison, although pypdf was faster (0.287 seconds versus 2.333 seconds).
- A kind of document neither parser handles well: scanned/image-only PDFs without an embedded text layer; both require OCR.

### One thing that went wrong today, and how I fixed it

- The Neon database hostname temporarily failed DNS resolution during a parser retry.
- I checked DNS resolution, waited for connectivity to recover, and reran the parser successfully. The second run confirmed 1,568 documents already parsed and zero failures.

English vs Tamil token experiment:
Hi (baseline): 233 tokens
English message: 241 tokens
Tamil message: 255 tokens
English message tokens: 8
Tamil message tokens: 22
Tamil needs 2.75 times more tokens than English.

Off-topic test:
Question: Who won the 2011 cricket world cup?
Result: Model replied "I am not sure."
Expected: Decline off-topic questions in one sentence.
Observation: It declined, but did not explain that cricket is outside ConsumerShield's subject.

Known-answer test 1:
Question: What is the time limit for filing a consumer complaint under the Consumer Protection Act, 2019?
Expected: Two years from the date the cause of action arises.
Result: Model answered correctly (two years).
Observation: Correct answer, but it was generated using Groq fallback.

Known-answer test 2:
Question: Can a consumer complaint be filed after two years?
Expected: Yes, if the District Commission is satisfied that there was sufficient cause for the delay.
Result: Model mentioned a possible extension but described it too narrowly.
Observation: Partially correct; needs more precise legal explanation.

Usage and billing verification:
- /v1/usage successfully displays daily calls, errors, fallbacks, tokens and estimated cost.
- Neon llm_calls table records individual provider attempts.
- Failed Gemini calls have status=error, tokens_in=0, tokens_out=0 and cost_inr=0.
- Successful Groq fallback calls have status=ok and fallback_used=true.
- Latency and estimated cost are recorded.
- Current estimated total cost: Rs 0.185.

## Day 08 — LLM gateway, fallback, streaming and usage tracking

### Part 1–4: LLM gateway and chat API

- Configured Gemini as the primary LLM provider.
- Configured Groq as the fallback provider.
- Added LLM settings to `config.py`, `.env` and `.env.example`.
- Added `httpx` for API requests.
- Added the `LlmCall` database model and Alembic migration.
- Implemented the LLM gateway with retry, fallback, circuit breaker and streaming support.
- Added `FakeLLM` for testing without real API calls.
- Added LLM usage recording and daily usage summaries.
- Created `prompts/chat_system_v1.md`.
- Implemented POST `/v1/chat` with streaming and JSON responses.
- Implemented GET `/v1/usage`.
- Added `scripts/ask.py` for testing the chat API.

### Tests and quality checks

- Gateway unit tests: 19 passed.
- Chat API tests: 7 passed.
- Full test suite: 78 passed.
- Ruff lint: all checks passed.
- Ruff formatting: 66 files already formatted after formatting.
- Local integration test requiring `TEST_DATABASE_URL` was skipped.

### Local chat verification

- Streaming response successfully tested.
- JSON response successfully tested.
- Gemini failures correctly triggered Groq fallback.
- Request IDs were recorded in the logs.
- Successful chat requests returned HTTP 200.
- An earlier consumer-rights question produced:
  - First words after: 8.48 seconds.
  - Total time: 9.20 seconds.
  - Input tokens: 247.
  - Output tokens: 476.
  - Provider: Groq fallback.

### Part 5: Break it on purpose

#### Tokens: English against Tamil

| Message | Tokens in |
|---|---:|
| "Hi" (baseline: mostly my system prompt) | 233 |
| English refund sentence | 241 |
| Same refund sentence in Tamil | 255 |

- English message tokens: 241 − 233 = 8.
- Tamil message tokens: 255 − 233 = 22.
- Tamil message needs approximately 2.75 times the tokens of English.

#### What the model does without my documents

- Question: "Will the seller refund me if I complain today?"
- The model admitted it could not know the particular seller's decision.
- Its response began: "I'm not sure whether this particular seller will refund you if you complain today."
- It then provided general guidance about return policies and complaint options.

**Off-topic test**

- Question: "Who won the 2011 cricket world cup?"
- Result: Model replied "I am not sure."
- Expected: Decline off-topic questions in one sentence.
- Observation: It declined, but did not explain that cricket is outside ConsumerShield's subject.

**Known-answer test 1**

- Question: What is the time limit for filing a consumer complaint under the Consumer Protection Act, 2019?
- Expected: Two years from the date the cause of action arises.
- Result: Model answered correctly (two years).
- Observation: Correct answer, but it was generated using Groq fallback.

**Known-answer test 2**

- Question: Can a consumer complaint be filed after two years?
- Expected: Yes, if the District Commission is satisfied that there was sufficient cause for the delay.
- Result: Model mentioned a possible extension but described it too narrowly.
- Observation: Partially correct; needs more precise legal explanation.

#### Fallback and circuit breaker

- Temporarily changed the primary model to `gemini-no-such-model`.
- Restarted the application.
- First three requests attempted Gemini and received HTTP 404 errors.
- Groq successfully answered all four requests.
- On the fourth request, the Gemini error stopped appearing in the logs because the circuit breaker was open.
- Waited 30 seconds.
- After the wait, Gemini was attempted again, demonstrating the half-open recovery attempt.
- The test model was replaced with the original configured value: `gemini-3.8-flash`.
- After restoring it, Gemini returned HTTP 429 Too Many Requests.
- Groq continued answering successfully.

**Result**

- Fallback mechanism: Passed.
- Circuit breaker opening: Passed.
- Half-open retry: Observed.
- Successful Gemini recovery: Not confirmed because of HTTP 429 rate limiting.

#### The bill

**`/v1/usage` verification**

| Metric | Value |
|---|---:|
| Date | 2026-11-25 |
| Calls | 30 |
| Errors | 14 |
| Fallbacks | 16 |
| Input tokens | 3,940 |
| Output tokens | 5,507 |
| Estimated cost | ₹0.185 |

**Neon database verification**

- Queried the latest 15 records from `llm_calls`.
- Failed Gemini calls were recorded with `status=error`.
- Failed Gemini calls had zero input and output tokens.
- Failed Gemini calls had zero estimated cost.
- Successful Groq calls were recorded with `status=ok`.
- Groq fallback calls had `fallback_used=true`.
- Latency and estimated cost were recorded.

**Result**

- `/v1/usage` successfully displays daily usage.
- Neon records individual provider attempts.
- Estimated total cost: Rs 0.185.

### Part 6: Ship it

#### Docker image

- Added `COPY --chown=app:app prompts ./prompts` immediately after the data COPY instruction in the Dockerfile.
- This ensures the prompt directory is included in the Docker image.

#### Render environment variables

- Added `GEMINI_API_KEY` to the Render service environment.
- Added `GROQ_API_KEY` to the Render service environment.
- Used the same values as the local `.env` file.
- API keys were not added to GitHub Secrets.

#### Local and live performance

- Primary: `gemini-3.8-flash` (Gemini).
- Fallback: `openai/gpt-oss-20b` (Groq).

- First question on my laptop:
  - First words after: 8.48 seconds.
  - Total: 9.20 seconds.
  - Tokens in: 247.
  - Tokens out: 476.
  - Cost: To be confirmed from the recorded call.

- Same question on my live URL (second, awake request):
  - First words after: Pending deployment test.
  - Day 1 target: under 1.5 seconds.

#### Deployment verification

- Dockerfile updated to include the prompts directory.
- Render environment variables saved.
- Git commit and push: Pending.
- Pull request and CI checks: Pending.
- Merge to main: Pending.
- Production deployment: Pending.
- Live `/health` verification: Pending.
- Live chat streaming test: Pending.
- Live `/v1/usage` verification: Pending.

#### One thing that went wrong today, and how I fixed it

- The intentionally invalid Gemini model returned HTTP 404.
- The circuit breaker stopped repeatedly calling the failed primary provider.
- Groq successfully handled fallback requests.
- After restoring the original Gemini model, Gemini returned HTTP 429 because of rate limiting.
- The application continued working through Groq fallback.

### Final Day 08 status

- LLM gateway implemented.
- Gemini and Groq configured.
- Streaming and JSON chat endpoints tested.
- Usage tracking implemented and verified.
- Fallback and circuit breaker tested.
- Neon usage records verified.
- Dockerfile updated to include prompts.
- Render API keys configured.
- Final deployment and live URL testing remain pending.


### Live production streaming test

- Production endpoint: `https://consumershield-82yz.onrender.com/v1/chat`
- Test question: What rights does a consumer have under the Consumer Protection Act 2019?
- Provider: Groq
- Model: `openai/gpt-oss-20b`
- First words latency: **1.40 seconds**
- Total response time: **1.62 seconds**
- Input tokens: 247
- Output tokens: 349
- Cost: ₹0.011706
- Attempts: 1
- Fallback used: Yes

**Result:** Live streaming successfully returned a response. The LLM gateway, fallback mechanism, and production usage tracking were verified.
