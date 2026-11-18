
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
