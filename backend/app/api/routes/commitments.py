from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse

from backend.app.api.deps import get_current_user
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
    current_user: Annotated[dict, Depends(get_current_user)],
):
    result, repeated = service.create_commitments(
        payload,
        str(idempotency_key),
        user_id=current_user["id"],
    )

    return JSONResponse(
        status_code=200 if repeated else 201,
        content=result,
    )


@router.get("")
def list_all(
    current_user: Annotated[dict, Depends(get_current_user)],
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
        user_id=current_user["id"],
    )


@router.get("/{commitment_id}")
def get_one(
    commitment_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    return service.get_commitment(
        str(commitment_id),
        user_id=current_user["id"],
    )


@router.patch("/{commitment_id}")
def update(
    commitment_id: UUID,
    payload: PatchCommitment,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    return service.update_commitment(
        str(commitment_id),
        payload,
        user_id=current_user["id"],
    )