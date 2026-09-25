import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_FILE)

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
_DEFAULT_LLM_PROVIDER = "ollama"
_DEFAULT_LLM_MODEL = "qwen2.5-coder:7b"
_DEFAULT_LLM_THINK = False
_DEFAULT_LLM_TIMEOUT_SECONDS = 120
_DEFAULT_LLM_MAX_TOKENS = 512
_DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_RAG_VECTOR_STORE_PATH = ""
_DEFAULT_RAG_EMBEDDING_BACKEND = "auto"
_DEFAULT_RAG_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


@dataclass(frozen=True)
class Settings:
    database_url: str
    storage_dir: Path
    max_upload_size_mb: int
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    cors_origins: tuple[str, ...]
    llm_provider: str
    llm_model: str
    llm_think: bool
    llm_timeout_seconds: int
    llm_max_tokens: int
    ollama_base_url: str
    rag_vector_store_path: str
    rag_embedding_backend: str
    rag_embedding_model: str


def _parse_cors_origins(raw: str) -> tuple[str, ...]:
    """Parse a comma-separated CORS_ORIGINS value into a tuple."""
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


def _parse_bool(raw: str) -> bool:
    """Parse a boolean environment value; anything else reads as False."""
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
    llm_provider = os.getenv("LLM_PROVIDER", _DEFAULT_LLM_PROVIDER).strip()
    llm_model = os.getenv("LLM_MODEL", _DEFAULT_LLM_MODEL).strip()
    llm_think = _parse_bool(
        os.getenv("LLM_THINK", str(_DEFAULT_LLM_THINK))
    )
    llm_timeout_seconds = int(
        os.getenv(
            "LLM_TIMEOUT_SECONDS", str(_DEFAULT_LLM_TIMEOUT_SECONDS)
        )
    )
    llm_max_tokens = int(
        os.getenv("LLM_MAX_TOKENS", str(_DEFAULT_LLM_MAX_TOKENS))
    )
    ollama_base_url = os.getenv(
        "OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE_URL
    ).strip()
    rag_vector_store_path = os.getenv(
        "RAG_VECTOR_STORE_PATH", _DEFAULT_RAG_VECTOR_STORE_PATH
    ).strip()
    rag_embedding_backend = os.getenv(
        "RAG_EMBEDDING_BACKEND", _DEFAULT_RAG_EMBEDDING_BACKEND
    ).strip()
    rag_embedding_model = os.getenv(
        "RAG_EMBEDDING_MODEL", _DEFAULT_RAG_EMBEDDING_MODEL
    ).strip()
    return Settings(
        database_url=database_url,
        storage_dir=storage_dir,
        max_upload_size_mb=max_upload_size_mb,
        jwt_secret_key=jwt_secret_key,
        jwt_algorithm=jwt_algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        cors_origins=cors_origins,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_think=llm_think,
        llm_timeout_seconds=llm_timeout_seconds,
        llm_max_tokens=llm_max_tokens,
        ollama_base_url=ollama_base_url,
        rag_vector_store_path=rag_vector_store_path,
        rag_embedding_backend=rag_embedding_backend,
        rag_embedding_model=rag_embedding_model,
    )