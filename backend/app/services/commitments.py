import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ValidationError

from backend.app.core.errors import AppError
from backend.app.domain.commitments import (
    apply_action,
    deadline,
    public_record,
    timestamp,
    utc_now,
)
from backend.app.repositories import commitments as repository
from backend.app.schemas.commitments import (
    AcceptedItem,
    CreateBatch,
    PatchCommitment,
    Values,
)

STATUSES = (
    "pending",
    "incomplete",
    "overdue",
    "completed",
    "discarded",
)


def create_commitments(
    payload: CreateBatch,
    key: str,
    now: datetime | None = None,
) -> tuple[dict, bool]:
    now = now or utc_now()
    normalized = payload.model_dump(mode="json")

    serialized = json.dumps(
        normalized,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    request_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    records = []

    for item in normalized["items"]:
        record = {
            **item["values"],
            "id": str(uuid4()),
            "analysis_id": normalized["analysis_id"],
            "candidate_id": item["candidate_id"],
            "reference_date": normalized["reference_date"],
            "source": normalized["source"],
            "extraction": item["extraction"],
            "resolved_ambiguities": item["resolved_ambiguities"],
            "lifecycle": "open",
            "created_at": timestamp(now),
            "updated_at": timestamp(now),
        }
        records.append(record)

    response = {
        "items": [public_record(record, now) for record in records]
    }

    return repository.create_batch(
        key,
        request_hash,
        records,
        response,
    )


def get_commitment(commitment_id: str) -> dict:
    return public_record(repository.get_record(commitment_id), utc_now())


def list_commitments(
    status: str | None,
    responsible: str | None,
    limit: int,
    offset: int,
    sort: str,
) -> dict:
    now = utc_now()
    records = repository.list_records()

    if responsible is not None:
        records = [
            record
            for record in records
            if record["responsible"] is not None
            and record["responsible"].casefold() == responsible.casefold()
        ]

    items = [public_record(record, now) for record in records]

    counts = {
        value: sum(item["status"] == value for item in items)
        for value in STATUSES
    }

    if status is not None:
        items = [item for item in items if item["status"] == status]

    # Orden estable: los empates conservan el orden por ID.
    items.sort(key=lambda item: item["id"])

    if sort == "created_desc":
        items.sort(key=lambda item: item["created_at"], reverse=True)
    else:
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

        def due_order(item):
            value = deadline(item)
            if value is None:
                return True, 0

            seconds = (value - epoch).total_seconds()
            return False, -seconds if sort == "due_desc" else seconds

        items.sort(key=due_order)

    return {
        "items": items[offset:offset + limit],
        "total": len(items),
        "limit": limit,
        "offset": offset,
        "counts": counts,
    }


def update_commitment(
    commitment_id: str,
    payload: PatchCommitment,
    now: datetime | None = None,
) -> dict:
    now = now or utc_now()

    def transform(record):
        values = {
            field: record[field]
            for field in Values.model_fields
        }
        values.update(
            {
                key: value
                for key, value in payload.changes.items()
                if key in Values.model_fields
            }
        )

        resolved = payload.changes.get(
            "resolved_ambiguities",
            record["resolved_ambiguities"],
        )

        try:
            validated = AcceptedItem.model_validate(
                {
                    "candidate_id": record["candidate_id"],
                    "values": values,
                    "extraction": record["extraction"],
                    "resolved_ambiguities": resolved,
                }
            )
        except ValidationError:
            raise AppError(
                "validation_error",
                "Los cambios contienen valores inválidos.",
                422,
            ) from None

        record.update(validated.values.model_dump(mode="json"))
        record["resolved_ambiguities"] = validated.resolved_ambiguities

        apply_action(record, payload.action, now)
        record["updated_at"] = timestamp(now)

        return record

    record = repository.update_record(commitment_id, transform)
    return public_record(record, now)