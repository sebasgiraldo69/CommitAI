import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    app_name: str
    log_level: str
    database_path: Path
    database_url: str | None
    timezone: str
    ai_provider: str
    ai_model: str
    ai_api_key: str
    ai_connect_timeout_seconds: float
    ai_read_timeout_seconds: float
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expire_minutes: int

    @property
    def ai_configured(self) -> bool:
        return (
            self.ai_provider != "unconfigured"
            and bool(self.ai_model)
            and bool(self.ai_api_key)
        )


def positive_number(name: str, default: str) -> float:
    try:
        value = float(os.getenv(name, default))
    except ValueError:
        raise ValueError(f"{name} debe ser un número positivo.") from None

    if not 0 < value < float("inf"):
        raise ValueError(f"{name} debe ser un número positivo y finito.")

    return value


@lru_cache
def get_settings() -> Settings:
    # Las variables de la terminal tienen prioridad sobre .env.
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    timezone = os.getenv("APP_TIMEZONE", "America/Bogota").strip()

    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("APP_TIMEZONE debe ser una zona IANA válida.") from None

    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("LOG_LEVEL no es válido.")

    database_path = Path(
        os.getenv("DATABASE_PATH", "data/commitai.db")
    ).expanduser()

    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path

    database_url = os.getenv("DATABASE_URL", "").strip() or None
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return Settings(
        app_name=os.getenv("APP_NAME", "CommitAI").strip() or "CommitAI",
        log_level=log_level,
        database_path=database_path.resolve(),
        database_url=database_url,
        timezone=timezone,
        ai_provider=(
            os.getenv("AI_PROVIDER", "unconfigured").strip()
            or "unconfigured"
        ),
        ai_model=os.getenv("AI_MODEL", "").strip(),
        ai_api_key=os.getenv("AI_API_KEY", "").strip(),
        ai_connect_timeout_seconds=positive_number(
            "AI_CONNECT_TIMEOUT_SECONDS", "5"
        ),
        ai_read_timeout_seconds=positive_number(
            "AI_READ_TIMEOUT_SECONDS", "35"
        ),
        jwt_secret_key=os.getenv(
            "JWT_SECRET_KEY", "commitai-dev-secret-key-change-in-production"
        ).strip(),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256").strip(),
        jwt_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "1440")),
    )