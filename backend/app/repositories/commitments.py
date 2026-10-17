import json

from backend.app.core.errors import AppError
from backend.app.db.database import connection


def get_record(commitment_id: str, user_id: str | None = None) -> dict:
    with connection() as conn:
        if user_id:
            row = conn.execute(
                """
                SELECT payload FROM commitments
                WHERE id = ? AND (user_id = ? OR user_id IS NULL)
                """,
                (commitment_id, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT payload FROM commitments WHERE id = ?",
                (commitment_id,),
            ).fetchone()

    if row is None:
        raise AppError(
            "commitment_not_found",
            "El compromiso no existe.",
            404,
        )

    return json.loads(row["payload"])


def list_records(user_id: str | None = None) -> list[dict]:
    with connection() as conn:
        if user_id:
            rows = conn.execute(
                """
                SELECT payload FROM commitments
                WHERE user_id = ? OR user_id IS NULL
                """,
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT payload FROM commitments"
            ).fetchall()

    return [json.loads(row["payload"]) for row in rows]


def create_batch(
    key: str,
    request_hash: str,
    records: list[dict],
    response: dict,
    user_id: str | None = None,
) -> tuple[dict, bool]:
    with connection() as conn:
        with conn:
            # Serializa escrituras para comprobar y guardar la clave
            # dentro de la misma transacción.
            conn.execute("BEGIN IMMEDIATE")

            previous = conn.execute(
                """
                SELECT request_hash, response_json
                FROM idempotency_keys
                WHERE key = ?
                """,
                (key,),
            ).fetchone()

            if previous:
                if previous["request_hash"] != request_hash:
                    raise AppError(
                        "idempotency_conflict",
                        "Esta clave ya se utilizó con otros datos.",
                        409,
                    )
                return json.loads(previous["response_json"]), True

            conn.executemany(
                """
                INSERT INTO commitments (id, payload, user_id)
                VALUES (?, ?, ?)
                """,
                [
                    (
                        record["id"],
                        json.dumps(record, ensure_ascii=False),
                        user_id,
                    )
                    for record in records
                ],
            )

            conn.execute(
                """
                INSERT INTO idempotency_keys
                    (key, request_hash, response_json)
                VALUES (?, ?, ?)
                """,
                (
                    key,
                    request_hash,
                    json.dumps(response, ensure_ascii=False),
                ),
            )

    return response, False


def update_record(
    commitment_id: str,
    transform,
    user_id: str | None = None,
) -> dict:
    with connection() as conn:
        with conn:
            conn.execute("BEGIN IMMEDIATE")

            if user_id:
                row = conn.execute(
                    """
                    SELECT payload FROM commitments
                    WHERE id = ? AND (user_id = ? OR user_id IS NULL)
                    """,
                    (commitment_id, user_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT payload FROM commitments WHERE id = ?",
                    (commitment_id,),
                ).fetchone()

            if row is None:
                raise AppError(
                    "commitment_not_found",
                    "El compromiso no existe.",
                    404,
                )

            record = transform(json.loads(row["payload"]))

            conn.execute(
                "UPDATE commitments SET payload = ? WHERE id = ?",
                (
                    json.dumps(record, ensure_ascii=False),
                    commitment_id,
                ),
            )

    return record