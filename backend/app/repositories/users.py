from uuid import uuid4

from backend.app.core.errors import AppError
from backend.app.db.database import IntegrityError, connection


def _format_user(row) -> dict | None:
    if row is None:
        return None
    data = dict(row)
    created_at = data.get("created_at")
    if hasattr(created_at, "isoformat"):
        data["created_at"] = created_at.isoformat()
    elif created_at is not None:
        data["created_at"] = str(created_at)
    return data


def get_user_by_email(email: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT id, email, hashed_password, created_at
            FROM users
            WHERE email = ?
            """,
            (email.strip().lower(),),
        ).fetchone()

    return _format_user(row)


def get_user_by_id(user_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT id, email, hashed_password, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    return _format_user(row)


def create_user(email: str, hashed_password: str) -> dict:
    user_id = str(uuid4())
    normalized_email = email.strip().lower()

    with connection() as conn:
        with conn:
            try:
                conn.execute(
                    """
                    INSERT INTO users (id, email, hashed_password)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, normalized_email, hashed_password),
                )
            except IntegrityError:
                raise AppError(
                    "email_already_registered",
                    "Este correo ya se encuentra registrado.",
                    409,
                ) from None

            row = conn.execute(
                """
                SELECT id, email, created_at
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()

    return _format_user(row)
