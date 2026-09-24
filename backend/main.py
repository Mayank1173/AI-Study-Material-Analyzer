import logging
import sys
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Repo root on sys.path so `rag` is importable when uvicorn runs from backend/.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.api.exceptions import register_exception_handlers
from app.api.router import api_router
from app.core.config import get_settings
from rag.answer import answer_question
from rag.knowledge_base import get_knowledge_base
from rag.llm import OllamaProvider

logger = logging.getLogger(__name__)

# Vite dev-server origins that must always be able to call the API.
_DEFAULT_CHAT_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1"
# Fallback user scope for the unauthenticated /api/chat demo endpoint.
_CHAT_USER_ID = "local-chat-user"

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "assets"
_INDEX_HTML = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "index.html"


class ChatRequest(BaseModel):
    question: str


@lru_cache
def _get_llm() -> OllamaProvider:
    return OllamaProvider(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL)


@lru_cache
def _get_kb():
    return get_knowledge_base()


def _chat_endpoint(request: ChatRequest) -> dict:
    """Answer a chat message through the RAG pipeline (Ollama + knowledge base)."""
    try:
        result = answer_question(
            _get_kb(),
            _get_llm(),
            query=request.question,
            user_id=_CHAT_USER_ID,
        )
    except Exception:
        logger.exception("chat pipeline failed")
        return {
            "answer": (
                "The language model is temporarily unavailable. "
                "Please try again later."
            ),
            "sources": [],
            "has_context": False,
        }

    return {
        "answer": result.answer,
        "sources": [
            {
                "source_index": s.source_index,
                "material_id": s.material_id,
                "course_id": s.course_id,
                "material_title": s.material_title,
                "original_filename": s.original_filename,
                "source_location": s.source_location,
                "score": s.score,
            }
            for s in result.sources
        ],
        "has_context": result.has_context,
        "model": result.model,
    }


async def _serve_react_app(full_path: str):
    if _INDEX_HTML.is_file():
        return FileResponse(str(_INDEX_HTML))
    return {
        "message": "AI Study Material Analyzer API is running",
        "status": "success",
    }


def create_app() -> FastAPI:
    """Build the application. Called once at import time.

    Creating the engine does not connect to PostgreSQL, so importing this
    module never requires a running database. Liveness/health/readiness are
    exposed through the /health router.
    """
    settings = get_settings()

    application = FastAPI(
        title="AI Study Material Analyzer API",
        description="Backend API for the AI-based study material analyzer",
        version="1.0.0",
        openapi_tags=[
            {
                "name": "Authentication",
                "description": "Register, login, and current-user endpoints",
            },
            {
                "name": "Users",
                "description": "User management (teacher-only)",
            },
            {
                "name": "Courses",
                "description": "Course management",
            },
            {
                "name": "Study Materials",
                "description": "Study material management",
            },
            {
                "name": "Health",
                "description": "Health and readiness checks",
            },
        ],
    )

    cors_origins = list(settings.cors_origins)
    for origin in _DEFAULT_CHAT_ORIGINS:
        if origin not in cors_origins:
            cors_origins.append(origin)

    has_wildcard = "*" in cors_origins
    if has_wildcard:
        logger.warning(
            "CORS_ORIGINS contains '*' which allows any origin. "
            "Wildcard origins are only safe for local development and "
            "credentials are disabled while it is configured."
        )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=not has_wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)

    application.include_router(api_router)

    application.post("/api/chat", tags=["Chat"])(_chat_endpoint)

    if _ASSETS_DIR.is_dir():
        application.mount(
            "/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="assets"
        )

    # Catch-all route: This MUST be the very last route defined
    application.get("/{full_path:path}", include_in_schema=False)(_serve_react_app)

    return application


app = create_app()
