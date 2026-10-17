import sqlite3
from contextlib import contextmanager

from backend.app.core.config import get_settings

try:
    import psycopg
    import psycopg.errors
    from psycopg.rows import dict_row

    IntegrityError = (sqlite3.IntegrityError, psycopg.errors.IntegrityError)
except ImportError:
    psycopg = None
    dict_row = None
    IntegrityError = (sqlite3.IntegrityError,)


class DBConnectionWrapper:
    def __init__(self, raw_conn, is_postgres: bool):
        self.raw_conn = raw_conn
        self.is_postgres = is_postgres
        self._tx = None

    def execute(self, query: str, params: tuple = ()):
        if self.is_postgres:
            if "BEGIN IMMEDIATE" in query:
                return self
            pg_query = query.replace("?", "%s")
            return self.raw_conn.execute(pg_query, params)
        return self.raw_conn.execute(query, params)

    def executemany(self, query: str, params_seq):
        if self.is_postgres:
            pg_query = query.replace("?", "%s")
            cursor = self.raw_conn.cursor()
            cursor.executemany(pg_query, params_seq)
            return cursor
        return self.raw_conn.executemany(query, params_seq)

    def commit(self):
        self.raw_conn.commit()

    def rollback(self):
        self.raw_conn.rollback()

    def __enter__(self):
        if self.is_postgres:
            self._tx = self.raw_conn.transaction()
            self._tx.__enter__()
        else:
            self.raw_conn.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_postgres and self._tx is not None:
            return self._tx.__exit__(exc_type, exc_val, exc_tb)
        return self.raw_conn.__exit__(exc_type, exc_val, exc_tb)

    def close(self):
        self.raw_conn.close()


@contextmanager
def connection():
    settings = get_settings()

    if settings.database_url:
        if psycopg is None:
            raise RuntimeError(
                "psycopg no está instalado. Ejecuta: pip install psycopg[binary]"
            )
        raw_conn = psycopg.connect(settings.database_url, row_factory=dict_row)
        wrapper = DBConnectionWrapper(raw_conn, is_postgres=True)
        try:
            yield wrapper
        finally:
            wrapper.close()
    else:
        path = settings.database_path
        path.parent.mkdir(parents=True, exist_ok=True)

        raw_conn = sqlite3.connect(path, timeout=5)
        raw_conn.row_factory = sqlite3.Row

        try:
            raw_conn.execute("PRAGMA foreign_keys = ON")
            wrapper = DBConnectionWrapper(raw_conn, is_postgres=False)
            yield wrapper
        finally:
            wrapper.close()


def initialize_database() -> None:
    with connection() as conn:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            v1_applied = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version = 1"
            ).fetchone()

            if not v1_applied:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS commitments (
                        id TEXT PRIMARY KEY,
                        payload TEXT NOT NULL,
                        user_id TEXT
                    )
                    """
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS idempotency_keys (
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
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                if not conn.is_postgres:
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