import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exceptions import register_exception_handlers
from app.api.router import api_router
from app.core.config import get_settings

logger = logging.getLogger(__name__)


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
                "name": "Courses",
                "description": "Subject creation and management",
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

    has_wildcard = "*" in settings.cors_origins
    if has_wildcard:
        logger.warning(
            "CORS_ORIGINS contains '*' which allows any origin. "
            "Wildcard origins are only safe for local development and "
            "credentials are disabled while it is configured."
        )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=not has_wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)

    application.include_router(api_router)

    @application.get("/", include_in_schema=False)
    def root():
        return {
            "message": "AI Study Material Analyzer API is running",
            "status": "success",
        }

    return application


app = create_app()