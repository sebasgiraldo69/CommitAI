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

            applied = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version = 1"
            ).fetchone()

            if applied:
                return

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