"""Document endpoints backed by PostgreSQL."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from consumershield.api.deps import DocumentRepositoryDep
from consumershield.db.repository import FILTER_KEY

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
async def list_documents(
    request: Request,
    repository: DocumentRepositoryDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """Search documents with optional metadata filters."""
    reserved = {"q", "limit", "offset"}
    filters: dict[str, str] = {}

    for key, value in request.query_params.multi_items():
        if key in reserved:
            continue

        if not FILTER_KEY.fullmatch(key):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid filter name: '{key}'.",
            )

        filters[key] = value

    total, items = await repository.list(
        q=q,
        filters=filters,
        limit=limit,
        offset=offset,
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": filters,
        "items": items,
    }


@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    repository: DocumentRepositoryDep,
) -> dict:
    """Retrieve one document by its external ID."""
    record = await repository.get(doc_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No document with id '{doc_id}'.",
        )

    return record
