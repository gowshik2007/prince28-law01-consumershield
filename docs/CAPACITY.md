# ConsumerShield Corpus Capacity Plan

## 1. Current Dataset Status

Latest corpus collection and dataset report:

| Metric | Measured value |
|---|---:|
| Registered sources | 1 |
| Downloaded source files | 1 |
| Downloaded source file size | 26,515,484 bytes (approximately 25.29 MiB) |
| Source dataset records | 74,484 |
| Consumer Protection Act, 2019 records extracted | 156 |
| Processed JSONL size | 207,129 bytes |
| Extracted characters (JSONL plus generated PDF) | 1,308,399 |
| Estimated tokens (JSONL plus generated PDF) | 327,100 |
| Estimated chunks | 468 |
| Manifest records | 1 |
| Download duration | 3.4 seconds |
| Repeat-run duration | 0.3 seconds |
| Repeat-run downloaded | 0 |
| Repeat-run skipped | 1 |
| Repeat-run blocked | 0 |
| Repeat-run failed | 0 |

Dataset: Open India Law - Central Indian Legislation Dataset.

The source dataset is distributed as a Parquet file. The processed corpus contains the matching Consumer Protection Act, 2019 records in JSONL format.

## 2. Processing Assumptions

| Parameter | Value |
|---|---:|
| PDF inspection limit | 5,000 pages |
| PDF pages inspected (generated test PDF) | 106 |
| Chunk size | 800 tokens |
| Chunk overlap | 100 tokens |
| Estimated token ratio | 4 characters per token |
| Embedding dimensions | 1,536 |
| Vector data type | float32 |

Token and chunk counts are estimates, not measurements from a production tokenizer or embedding pipeline. A generated test PDF was inspected: 106 pages, all with extractable text. This is a derived test artifact, not an original government PDF.

## 3. Vector Storage Estimate

Each vector requires:

1,536 dimensions x 4 bytes = 6,144 bytes.

For the current estimated 468 chunks:

468 x 6,144 = 2,875,392 bytes, approximately 2.74 MiB.

| Number of chunks | Approximate raw vector storage |
|---:|---:|
| 468 (current estimate) | 2.74 MiB |
| 1,000 | 5.86 MiB |
| 5,000 | 29.30 MiB |
| 10,000 | 58.59 MiB |
| 50,000 | 292.97 MiB |
| 100,000 | 585.94 MiB |

Actual database storage will be higher because of indexes, metadata, and database overhead.

## 4. Embedding Cost

The dataset report uses an assumed price of $0.02 per million input tokens.

For the current estimated 327,100 tokens:

327,100 / 1,000,000 x $0.02 = approximately $0.006542.

At the planning exchange rate of ₹95 per USD, this is approximately ₹0.10.

This is a planning estimate only. No embedding API usage or billing has been measured. Confirm the actual embedding provider and model price before production use.

## 5. Database Capacity

Production database capacity was checked using PostgreSQL.

| Metric | Measured value |
|---|---:|
| Current database size | 8,069,120 bytes |
| Current database size | Approximately 7.70 MiB |
| Neon plan | Free |
| Included PostgreSQL storage | 1 GB |
| Included compute | 100 hours/month |
| Included network transfer | 5 GB/month |
| Approximate storage usage | 0.75% |
| Approximate remaining storage | 992 MiB |

The database size includes existing application data and is not exclusively corpus storage.

The estimated current raw vector storage is approximately 1.83 MiB. The current estimated text and vector data are small compared with the available 1 GB storage allowance. Indexes, metadata, application growth, and other database overhead must still be considered.

## 6. Download and Recovery Verification

Initial download:

```text
sources=1 downloaded=1 skipped=0 blocked=0 failed=0 seconds=3.4
```

Repeat run:

```text
sources=1 downloaded=0 skipped=1 blocked=0 failed=0 seconds=0.3
```

The repeat run confirms that an already downloaded file is skipped instead of downloaded again.

A dedicated automated test was added for resumable downloads. It simulates an interrupted download followed by a successful HTTP 206 Partial Content response using a byte-range request.

An active HTTP transfer was interrupted against a local HTTP test server. The downloader preserved 524,288 bytes, resumed from byte 524,288 with HTTP 206 Partial Content, and reconstructed the 8,388,608-byte payload with a matching SHA-256 checksum. An external-source interruption has not been tested.

## 7. Ten-Times Growth Estimate

If the current processed corpus grows by ten times:

| Metric | Approximate estimate |
|---|---:|
| Characters | 13,083,990 |
| Tokens | 3,271,000 |
| Chunks | 4,673 |
| Raw vector storage | 27.38 MiB |
| Embedding cost | $0.06542 |
| Embedding cost at ₹95/USD | Approximately ₹0.98 |

These are linear planning estimates. Actual storage will be higher after indexes, metadata, and database overhead.

## 8. Capacity Planning Questions and Answers

### Q1. How much source data has been collected?

One Parquet source file was downloaded successfully. It contains 74,484 source records. The matching Consumer Protection Act, 2019 records were extracted into a processed JSONL file containing 156 records.

### Q2. How much processing capacity does the current corpus require?

The combined report inventory contains 1,308,399 extracted characters, approximately 327,100 estimated tokens, and 468 estimated chunks. This includes both processed JSONL text and a generated PDF derived from that text, so it double-counts some content.

### Q3. What is the estimated vector storage requirement?

At 1,536 dimensions and float32 precision, 468 estimated vectors require approximately 2.74 MiB of raw vector storage. Database indexes and metadata will increase actual storage requirements.

### Q4. What is the estimated embedding cost?

At the report's assumed rate of $0.02 per million tokens, processing 327,100 estimated tokens would cost approximately $0.006542, or about ₹0.10 at ₹95 per USD. This is not actual provider billing.

### Q5. What is the least certain capacity assumption?

The token estimate uses a rough ratio of four characters per token, not a production tokenizer. The generated test PDF had 106 pages and 432,954 extractable characters, averaging approximately 4,084.5 characters per page or 1,021 estimated tokens per page. This is a derived test document, not an original source PDF.

### Q6. Can the current corpus fit in the free database plan?

The current database uses approximately 7.70 MiB of the 1 GB storage allowance. The estimated raw vectors require approximately 2.74 MiB. The current corpus is small enough for the available storage, although indexes, metadata, and future application growth must be monitored.

### Q7. What happens if the corpus grows ten times?

At ten times the current combined estimate, processing would be approximately 3,271,000 tokens, 4,673 chunks, and 27.38 MiB of raw vectors. Estimated embedding cost would be approximately $0.06542. This remains small compared with the 1 GB storage allowance, before database overhead.

## 9. Storage and Deployment Considerations

- Keep downloaded source documents under `data/raw/`.
- Do not commit downloaded corpus files to Git.
- Keep `data/manifest.jsonl` for download tracking.
- Keep processed, application-ready data under `data/processed/`.
- Monitor database storage, compute, network transfer, and deployment resources.
- Use incremental ingestion instead of repeatedly processing the entire corpus.
- Preserve source attribution and licence information.
- Check source permissions and robots policies before downloading.
- Test PDF extraction for scanned pages and missing text before relying on PDF page estimates.

## 10. Known Gaps

- Current collection contains one registered dataset source.
- Only Consumer Protection Act, 2019 records have been extracted into the processed corpus.
- The full target of Acts, rules, guidelines, 100 orders, additional orders, and CCPA notices has not yet been collected.
- India Code automated access requires written permission.
- The previously investigated data.gov.in resource was unusable.
- The only PDF inspected so far is a generated test artifact derived from processed JSONL text; no original government-source PDF has been inspected.
- Parquet files are not extracted directly by the dataset report; the processed JSONL is inspected.
- Actual embedding usage and billing have not been measured.
- A real TCP interruption and HTTP 206 byte-range resume were demonstrated against a local test server; an external-source interruption has not been tested.
- Incremental corpus ingestion still needs end-to-end verification.

## 11. Completion Criteria

- [x] Approved dataset source registered in `data/sources.csv`.
- [x] Dataset licence recorded in the source register.
- [x] Downloader implementation and tests merged into main.
- [x] Source downloaded and recorded in the manifest.
- [x] Processed Consumer Protection Act corpus generated.
- [x] Dataset report generated.
- [x] Capacity estimates calculated and documented.
- [x] Repeat-run skip behaviour verified.
- [x] Automated interrupted-download and HTTP 206 resume test passed.
- [x] Production database size checked.
- [ ] Full target corpus collected.
- [x] PDF page extraction and tokens-per-page measured on a generated test PDF (not an original source PDF).
- [x] Local HTTP interruption and byte-range resume demonstrated; external-source interruption remains untested.
- [ ] Incremental corpus ingestion tested end to end.

## Latest verified status — 23 November 2026

- Processed legislation records: 371 across three Act JSONL files.
- Processed CCPA order-listing metadata records: 96.
- Combined processed records: 467 (legislation and listing metadata; not all full legal documents).
- CCPA full order documents downloaded: 0.
- Dataset report: 1,308,399 combined characters, approximately 327,100 tokens, and 468 estimated chunks; some content is duplicated between JSONL and the generated PDF.
- Source register: 1 registered source (Open India Law).
- Automated tests: 36 passed.
- Ruff lint: passed.
- Ruff format check: 46 files already formatted.

### Remaining work

- Reach the 100-record CCPA listing target: 4 additional records.
- Obtain and process full CCPA order documents only after access permission and licence terms are verified.
- Complete the required rules and guidelines corpus.
- Reconcile capacity estimates with the latest dataset report.


## Latest dataset measurements

These figures come from the regenerated `DATASET.md` report:

| Metric | Latest value |
|---|---:|
| Extracted characters (JSONL plus generated PDF) | 1,308,399 |
| Estimated tokens (JSONL plus generated PDF) | 327,100 |
| Estimated chunks | 468 |
| Estimated raw vector storage | 2.74 MiB |
| Estimated embedding cost at $0.02/million tokens | $0.006542 |
| PDF pages inspected (generated test PDF) | 106 |

The generated test PDF has 106 pages, all with extractable text, averaging approximately 4,084.5 characters or 1,021 estimated tokens per page. It is not an original government-source PDF. The four capacity answers above remain planning estimates where applicable.


### Additional recovery test evidence (23 November 2026)

An active transfer was interrupted against a local HTTP test server. The downloader preserved 524,288 bytes, resumed from byte 524,288 with HTTP 206 Partial Content, and reconstructed the 8,388,608-byte payload with a matching SHA-256 checksum. This verifies interruption and byte-range resume locally; an external-source interruption remains untested.


## Generated PDF capacity test (23 November 2026)

A reproducible test PDF was generated from the three processed legislation JSONL files using `scripts/build_capacity_test_pdf.py`. It is a derived test artifact, not an original government publication or a separately collected source.

| Measurement | Result |
|---|---:|
| Input legislation records | 371 |
| Source text characters | 410,168 |
| Generated PDF size | 298,163 bytes |
| Actual PDF pages | 106 |
| Pages with extractable text | 106 |
| Pages without extractable text | 0 |
| Extracted PDF characters | 432,954 |
| Estimated PDF tokens (characters / 4) | 108,238 |
| Average extracted characters per page | 4,084.5 |
| Estimated tokens per page | 1,021 |
| Estimated chunks (800 tokens, 100 overlap) | 155 |

The regenerated `DATASET.md` inventory includes both the processed JSONL files and this generated PDF. Its combined totals are 1,308,399 extracted characters, approximately 327,100 tokens, and 468 estimated chunks. Because the PDF was generated from the JSONL text, these combined totals include duplicate representations of some legal content and should not be interpreted as unique-source corpus size.

The generated PDF test verifies extraction of text from all 106 pages. It does not establish extraction quality for scanned or externally sourced PDFs.
