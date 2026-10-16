from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.app.core.errors import AppError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def deadline(record: dict) -> datetime | None:
    if record["due_date"] is None:
        return None

    due_date = date.fromisoformat(record["due_date"])
    zone = ZoneInfo(record["timezone"])

    if record["due_time"] is not None:
        due_time = time.fromisoformat(record["due_time"])
        local = datetime.combine(due_date, due_time, tzinfo=zone)
    else:
        # Sin hora, vence al comenzar el día siguiente.
        # Evitar desbordamiento para la fecha máxima representable.
        if due_date == date.max:
            local = datetime.combine(due_date, time.max, tzinfo=zone)
        else:
            local = datetime.combine(
                due_date + timedelta(days=1),
                time.min,
                tzinfo=zone,
            )

    return local.astimezone(timezone.utc)


def missing_information(record: dict) -> list[str]:
    missing = []

    if record["responsible"] is None:
        missing.append("responsible")

    if record["due_date"] is None:
        missing.append("due_date")

    resolved = set(record["resolved_ambiguities"])
    ambiguous = {
        item["field"] for item in record["extraction"]["ambiguities"]
    }

    if "due_time" in ambiguous and "due_time" not in resolved:
        missing.append("due_time")

    return missing


def public_record(record: dict, now: datetime) -> dict:
    result = {
        key: value
        for key, value in record.items()
        if key != "lifecycle"
    }

    limit = deadline(record)
    is_past_due = limit is not None and now >= limit

    if record["lifecycle"] in {"completed", "discarded"}:
        status = record["lifecycle"]
    elif record["responsible"] is None or record["due_date"] is None:
        status = "incomplete"
    elif is_past_due:
        status = "overdue"
    else:
        status = "pending"

    result.update(
        status=status,
        is_past_due=is_past_due,
        missing_information=missing_information(record),
    )
    return result


def apply_action(record: dict, action: str | None, now: datetime) -> None:
    if action is None:
        return

    if action == "complete":
        record["lifecycle"] = "completed"
    elif action == "discard":
        record["lifecycle"] = "discarded"
    else:
        record["lifecycle"] = "open"

        if action.startswith("set_"):
            requested = action.removeprefix("set_")
            actual = public_record(record, now)["status"]

            if requested != actual:
                raise AppError(
                    "invalid_transition",
                    f"Los datos corresponden al estado '{actual}'.",
                    409,
                )