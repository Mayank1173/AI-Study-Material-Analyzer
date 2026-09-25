"""Aggregates all public API routers.

The public path contract is stable and must remain compatible:

    /api/auth/*
    /api/courses/*
    /api/materials/*
    /api/chat
    /health/*
"""
from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.courses import router as courses_router
from app.api.routes.health import router as health_router
from app.api.routes.materials import router as materials_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(courses_router)
api_router.include_router(materials_router)
api_router.include_router(chat_router)

__all__ = ["api_router"]