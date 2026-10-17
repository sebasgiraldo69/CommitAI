import sqlite3
from contextlib import contextmanager

from backend.app.core.config import get_settings


@contextmanager
def connection():
    path = get_settings().database_path
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    finally:
        conn.close()


def initialize_database() -> None:
    with connection() as conn:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            v1_applied = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version = 1"
            ).fetchone()

            if not v1_applied:
                conn.execute(
                    """
                    CREATE TABLE commitments (
                        id TEXT PRIMARY KEY,
                        payload TEXT NOT NULL
                    )
                    """
                )

                conn.execute(
                    """
                    CREATE TABLE idempotency_keys (
                        key TEXT PRIMARY KEY,
                        request_hash TEXT NOT NULL,
                        response_json TEXT NOT NULL
                    )
                    """
                )

                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (1)"
                )

            v2_applied = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version = 2"
            ).fetchone()

            if not v2_applied:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        hashed_password TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                columns = [
                    row[1]
                    for row in conn.execute(
                        "PRAGMA table_info(commitments)"
                    ).fetchall()
                ]
                if "user_id" not in columns:
                    conn.execute(
                        "ALTER TABLE commitments ADD COLUMN user_id TEXT"
                    )
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_commitments_user_id "
                        "ON commitments(user_id)"
                    )

                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (2)"
                )