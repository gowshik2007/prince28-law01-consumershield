
## Day 2 — Database migrations

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


## Day 3 — Idempotent loader

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
