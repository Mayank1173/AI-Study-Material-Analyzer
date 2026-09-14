import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://postgres:postgres@localhost:5432/ai_study_analyzer"
)
_DEFAULT_STORAGE_DIR = str(Path(__file__).resolve().parents[2] / "storage")
_DEFAULT_MAX_UPLOAD_SIZE_MB = 20
_DEFAULT_JWT_SECRET_KEY = "change-me-in-production"
_DEFAULT_JWT_ALGORITHM = "HS256"
_DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


@dataclass(frozen=True)
class Settings:
    database_url: str
    storage_dir: Path
    max_upload_size_mb: int
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    cors_origins: tuple[str, ...]


def _parse_cors_origins(raw: str) -> tuple[str, ...]:
    """Parse a comma-separated CORS_ORIGINS value into a tuple."""
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


@lru_cache
def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", _DEFAULT_DATABASE_URL).strip()
    storage_dir = Path(os.getenv("STORAGE_DIR", _DEFAULT_STORAGE_DIR))
    max_upload_size_mb = int(
        os.getenv("MAX_UPLOAD_SIZE_MB", str(_DEFAULT_MAX_UPLOAD_SIZE_MB))
    )
    jwt_secret_key = os.getenv(
        "JWT_SECRET_KEY", _DEFAULT_JWT_SECRET_KEY
    ).strip()
    jwt_algorithm = os.getenv("JWT_ALGORITHM", _DEFAULT_JWT_ALGORITHM).strip()
    access_token_expire_minutes = int(
        os.getenv(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            str(_DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES),
        )
    )
    cors_origins = _parse_cors_origins(
        os.getenv("CORS_ORIGINS", ",".join(_DEFAULT_CORS_ORIGINS))
    )
    return Settings(
        database_url=database_url,
        storage_dir=storage_dir,
        max_upload_size_mb=max_upload_size_mb,
        jwt_secret_key=jwt_secret_key,
        jwt_algorithm=jwt_algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        cors_origins=cors_origins,
    )