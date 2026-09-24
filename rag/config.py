"""Environment-driven settings for the Phase 2 knowledge base.

All knobs have safe, local, deterministic defaults so the knowledge base
works out of the box and tests never need live services or model downloads.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RagSettings:
    vector_store_path: Path
    embedding_backend: str
    embedding_model: str


def _default_store_path() -> Path:
    return Path(__file__).resolve().parent / "rag_data" / "knowledge_base.db"


def get_rag_settings(
    *,
    vector_store_path: str | os.PathLike[str] | None = None,
    embedding_backend: str | None = None,
    embedding_model: str | None = None,
) -> RagSettings:
    """Build settings from explicit args, falling back to environment then defaults."""
    raw_path = vector_store_path or os.environ.get("RAG_VECTOR_STORE_PATH")
    store_path = Path(raw_path).resolve() if raw_path else _default_store_path()
    return RagSettings(
        vector_store_path=store_path,
        embedding_backend=embedding_backend
        or os.environ.get("RAG_EMBEDDING_BACKEND", "auto"),
        embedding_model=embedding_model
        or os.environ.get("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
    )