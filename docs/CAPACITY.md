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

Dataset: Open India Law — Central Indian Legislation Dataset.

The source dataset is distributed as a Parquet file. The processed corpus contains the matching Consumer Protection Act, 2019 records in JSONL format.

## 2. Processing Assumptions

| Parameter | Value |
|---|---:|
| PDF inspection limit | 5,000 pages |
| Chunk size | 800 tokens |
| Chunk overlap | 100 tokens |
| Estimated token ratio | 4 characters per token |
| Embedding dimensions | 1,536 |
| Vector data type | float32 |

Token and chunk counts are estimates, not measurements from a production tokenizer or embedding pipeline.

## 3. Vector Storage Estimate

Each vector requires:

1,536 dimensions × 4 bytes = 6,144 bytes.

For the current estimated 74 chunks:

74 × 6,144 = 454,656 bytes, approximately 0.43 MiB.

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

51,655 / 1,000,000 × $0.02 = approximately $0.001033.

This is a planning estimate only. No embedding API usage or billing has been measured. Confirm the actual embedding provider and model price before production use.

## 5. Capacity Planning Questions and Answers

### Q1. How much source data has been collected?

One Parquet source file was downloaded successfully. It contains 74,484 source records. The matching Consumer Protection Act, 2019 records were extracted into a processed JSONL file containing 156 records.

### Q2. How much processing capacity does the current corpus require?

The processed text contains 206,619 characters, approximately 51,655 estimated tokens, and approximately 74 chunks using the current 800-token chunk size and 100-token overlap.

### Q3. What is the estimated vector storage requirement?

At 1,536 dimensions and float32 precision, 74 estimated vectors require approximately 0.43 MiB of raw vector storage. Database indexes and metadata will increase actual storage requirements.

### Q4. What is the estimated embedding cost?

At the report's assumed rate of $0.02 per million tokens, processing 51,655 estimated tokens would cost approximately $0.001033. This is not a verified provider quotation or actual billing amount.

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

A forced interruption and partial-file resume test has not yet been demonstrated. The skip test must not be treated as proof of byte-range resume capability.

## 7. Storage and Deployment Considerations

- Keep downloaded source documents under `data/raw/`.
- Do not commit downloaded corpus files to Git.
- Keep `data/manifest.jsonl` for download tracking.
- Keep processed, application-ready data under `data/processed/`.
- Check actual database and hosting plan limits before loading the corpus.
- Monitor database storage, request limits, memory, and deployment resources.
- Use incremental ingestion instead of repeatedly processing the entire corpus.
- Preserve source attribution and licence information.

## 8. Known Gaps

- Current collection contains one registered dataset source.
- Only Consumer Protection Act, 2019 records have been extracted into the processed corpus.
- India Code automated access requires written permission.
- The previously investigated data.gov.in resource was unusable.
- Source permissions and robots policies must be checked before downloading.
- PDF extraction must be tested for scanned pages and missing text.
- Parquet files are not extracted directly by the dataset report; the processed JSONL is inspected.
- Actual embedding usage and production database capacity have not been measured.
- Partial-download interruption and resume have not yet been demonstrated.

## 9. Completion Criteria

- [x] Approved dataset source registered in `data/sources.csv`.
- [x] Dataset licence recorded in the source register.
- [x] Downloader implementation and tests merged into main.
- [x] Source downloaded and recorded in the manifest.
- [x] Processed Consumer Protection Act corpus generated.
- [x] Dataset report generated.
- [x] Capacity estimates calculated and documented.
- [x] Repeat-run skip behaviour verified.
- [ ] Forced interruption and partial-download resume tested, if required.
- [ ] Database capacity confirmed before production-scale ingestion.
- [ ] Incremental corpus ingestion tested.
