
# Ingestion report

<!-- generated:start -->
_Generated 27 Nov 2026 15:30 from the database._

| What | Count |
|---|---|
| Documents in the database | 1534 |
| Pages | 29252 |
| Tokens of text (characters ÷ 4) | 20,298,668 |
| Files the parser gave up on | 1 |
| Documents with an extracted record | 69 |
| Documents whose extraction failed | 0 |

| Queue | Count |
|---|---|
| Ingest jobs started | 2 |
| Items finished (done or skipped) | 6 |
| Items that needed more than one try | 0 |
| Items in the dead-letter list | 2 |

Model calls for extraction: 156 · tokens in 255,791 · tokens out 39,691 · cost at list price Rs 5.90

Last job `f92fac6958c24064a344d916fa198e87`: 1 requested, 0 ok, 1 failed, 0.1 minutes.

Dead-letter list by stage: parse 2
<!-- generated:end -->

## What I learnt

1. I learnt how Redis and ARQ workers process document ingestion jobs in the background.
2. I learnt that unsupported file formats can cause parsing failures, which are recorded in the dead-letter list.
3. I learnt how to generate a database report to track documents, pages, tokens, model costs, and failures.
