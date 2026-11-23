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
| Extracted characters | 206,619 |
| Estimated tokens | 51,655 |
| Estimated chunks | 74 |
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
| PDF pages currently inspected | 0 |
| Chunk size | 800 tokens |
| Chunk overlap | 100 tokens |
| Estimated token ratio | 4 characters per token |
| Embedding dimensions | 1,536 |
| Vector data type | float32 |

Token and chunk counts are estimates, not measurements from a production tokenizer or embedding pipeline. No PDF pages are currently available for measuring tokens per page.

## 3. Vector Storage Estimate

Each vector requires:

1,536 dimensions x 4 bytes = 6,144 bytes.

For the current estimated 74 chunks:

74 x 6,144 = 454,656 bytes, approximately 0.43 MiB.

| Number of chunks | Approximate raw vector storage |
|---:|---:|
| 74 (current estimate) | 0.43 MiB |
| 1,000 | 5.86 MiB |
| 5,000 | 29.30 MiB |
| 10,000 | 58.59 MiB |
| 50,000 | 292.97 MiB |
| 100,000 | 585.94 MiB |

Actual database storage will be higher because of indexes, metadata, and database overhead.

## 4. Embedding Cost

The dataset report uses an assumed price of $0.02 per million input tokens.

For the current estimated 51,655 tokens:

51,655 / 1,000,000 x $0.02 = approximately $0.001033.

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

The estimated current raw vector storage is approximately 0.43 MiB. The current estimated text and vector data are small compared with the available 1 GB storage allowance. Indexes, metadata, application growth, and other database overhead must still be considered.

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

This verifies the resume logic in a mocked test. It does not claim that a real live network download was manually interrupted and resumed.

## 7. Ten-Times Growth Estimate

If the current processed corpus grows by ten times:

| Metric | Approximate estimate |
|---|---:|
| Characters | 2,066,190 |
| Tokens | 516,550 |
| Chunks | 740 |
| Raw vector storage | 4.34 MiB |
| Embedding cost | $0.01033 |
| Embedding cost at ₹95/USD | Approximately ₹0.98 |

These are linear planning estimates. Actual storage will be higher after indexes, metadata, and database overhead.

## 8. Capacity Planning Questions and Answers

### Q1. How much source data has been collected?

One Parquet source file was downloaded successfully. It contains 74,484 source records. The matching Consumer Protection Act, 2019 records were extracted into a processed JSONL file containing 156 records.

### Q2. How much processing capacity does the current corpus require?

The processed text contains 206,619 characters, approximately 51,655 estimated tokens, and approximately 74 chunks using the current 800-token chunk size and 100-token overlap.

### Q3. What is the estimated vector storage requirement?

At 1,536 dimensions and float32 precision, 74 estimated vectors require approximately 0.43 MiB of raw vector storage. Database indexes and metadata will increase actual storage requirements.

### Q4. What is the estimated embedding cost?

At the report's assumed rate of $0.02 per million tokens, processing 51,655 estimated tokens would cost approximately $0.001033, or about ₹0.10 at ₹95 per USD. This is not actual provider billing.

### Q5. What is the least certain capacity assumption?

The token estimate uses a rough ratio of four characters per token. A production tokenizer and actual PDF text extraction are needed for a more accurate measurement. No PDF pages have currently been inspected, so tokens per page cannot yet be measured.

### Q6. Can the current corpus fit in the free database plan?

The current database uses approximately 7.70 MiB of the 1 GB storage allowance. The estimated raw vectors require approximately 0.43 MiB. The current corpus is small enough for the available storage, although indexes, metadata, and future application growth must be monitored.

### Q7. What happens if the corpus grows ten times?

The estimate becomes approximately 516,550 tokens, 740 chunks, and 4.34 MiB of raw vectors. The estimated embedding cost becomes approximately $0.01033. This remains small compared with the 1 GB storage allowance, before database overhead.

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
- No PDF pages have currently been inspected.
- Parquet files are not extracted directly by the dataset report; the processed JSONL is inspected.
- Actual embedding usage and billing have not been measured.
- Resume behaviour has an automated mocked test, but a real live network interruption has not been demonstrated.
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
- [ ] PDF page extraction and tokens-per-page measurement completed.
- [ ] Real live network interruption and resume demonstrated.
- [ ] Incremental corpus ingestion tested end to end.
