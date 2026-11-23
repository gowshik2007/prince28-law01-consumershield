
# ConsumerShield Corpus Capacity Plan

## 1. Current Dataset Status

The initial dataset report found:

- Downloaded files: 0
- PDF files: 0
- Extracted pages: 0
- Estimated tokens: 0
- Estimated chunks: 0
- Manifest records: 0

The downloader and reporting scripts are implemented, but corpus collection is not yet complete.

## 2. Processing Assumptions

| Parameter | Planning value |
|---|---:|
| PDF inspection limit | 5,000 pages |
| Chunk size | 800 tokens |
| Chunk overlap | 100 tokens |
| Estimated token ratio | 4 characters per token |
| Embedding dimensions | 1,536 |
| Vector data type | float32 |

These are planning assumptions, not measured production values.

## 3. Vector Storage Estimate

Each vector requires:

1,536 dimensions × 4 bytes = 6,144 bytes.

| Number of chunks | Approximate raw vector storage |
|---:|---:|
| 1,000 | 5.86 MiB |
| 5,000 | 29.30 MiB |
| 10,000 | 58.59 MiB |
| 50,000 | 292.97 MiB |
| 100,000 | 585.94 MiB |

Actual database storage will be higher because of indexes, metadata, and database overhead.

## 4. Embedding Cost

The dataset report currently uses a configurable placeholder of $0.02 per million input tokens.

This is an estimation parameter only. Confirm the actual embedding provider and model price before budgeting or production use.

## 5. Storage and Deployment Considerations

- Keep downloaded source documents under `data/raw/`.
- Do not commit downloaded corpus files to Git.
- Keep `data/manifest.jsonl` for download tracking.
- Check the actual database and hosting plan limits before loading the complete corpus.
- Monitor database storage, request limits, memory, and deployment resource usage.
- Use incremental ingestion rather than repeatedly processing the entire corpus.

## 6. Known Limitations and Next Steps

- The current corpus is empty.
- Source permissions and website crawling policies must be checked before downloading.
- The target collection of legislation, rules, guidelines, and consumer orders remains outstanding.
- PDF extraction must be checked for scanned pages and missing text.
- Actual chunk counts and storage requirements must be measured after ingestion.

## 7. Completion Criteria

- [ ] Approved sources registered in `data/sources.csv`.
- [ ] Source permissions and robots policies checked.
- [ ] Documents downloaded and recorded in the manifest.
- [ ] Dataset report generated.
- [ ] PDF extraction and chunk estimates reviewed.
- [ ] Database capacity confirmed.
- [ ] Corpus ingestion tested incrementally.
