from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse

from backend.app.schemas.commitments import (
    CreateBatch,
    PatchCommitment,
    Status,
)
from backend.app.services import commitments as service

router = APIRouter(prefix="/commitments", tags=["commitments"])


@router.post("")
def create(
    payload: CreateBatch,
    idempotency_key: Annotated[UUID, Header()],
):
    result, repeated = service.create_commitments(
        payload,
        str(idempotency_key),
    )

    return JSONResponse(
        status_code=200 if repeated else 201,
        content=result,
    )


@router.get("")
def list_all(
    status: Status | None = None,
    responsible: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: Literal["due_asc", "due_desc", "created_desc"] = "due_asc",
):
    return service.list_commitments(
        status,
        responsible,
        limit,
        offset,
        sort,
    )


@router.get("/{commitment_id}")
def get_one(commitment_id: UUID):
    return service.get_commitment(str(commitment_id))


@router.patch("/{commitment_id}")
def update(commitment_id: UUID, payload: PatchCommitment):
    return service.update_commitment(str(commitment_id), payload)