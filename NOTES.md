
## Day 2 â€” Database migrations

### Migration history

```text
5ce2b0a92557 -> 13e79d5f23f5 (head), add gin index on metadata
<base> -> 5ce2b0a92557, create documents and pages
```

### Verification

- Migration 1: Created documents and pages tables.
- Migration 2: Added GIN index on documents.metadata.
- Downgrade -1: Successful.
- Alembic current: 5ce2b0a92557.
- Upgrade head: Successful.
- Alembic history: Both migrations verified.


## Day 3 â€” Idempotent loader

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

## Day 6 â€” EXPLAIN and GIN index

### Query used

```text
python -m uv run python scripts/explain.py product_category "E-commerce goods and services"
```

### EXPLAIN output â€” Normal planner

```text
Seq Scan on documents  (cost=0.00..11.00 rows=1 width=36) (actual time=0.814..0.817 rows=1.00 loops=1)
Filter: (metadata @> '{"product_category": "E-commerce goods and services"}'::jsonb)
Rows Removed by Filter: 4
Execution Time: 0.846 ms
```

### EXPLAIN output â€” Sequential scan disabled

```text
Bitmap Heap Scan on documents  (cost=12.81..16.82 rows=1 width=36) (actual time=2.038..2.039 rows=1.00 loops=1)
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
## Day 4 Â· Docker, Compose and tests

### The image

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
