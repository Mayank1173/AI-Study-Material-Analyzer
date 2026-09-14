"""Consistent JSON error responses.

Every handled error is returned as FastAPI's standard ``{"detail": ...}`` body
(kept for backward compatibility) enriched with a machine-readable envelope:

    {
      "detail": "Course with id ... was not found",
      "error": {
        "code": "RESOURCE_NOT_FOUND",
        "message": "Course with id ... was not found"
      }
    }

FastAPI's default validation behavior for 422 responses is preserved: the
standard ``detail`` list is left untouched and the ``error`` envelope is added
alongside it. Sensitive information (stack traces, secrets, internal paths) is
never included by these handlers because the message is taken from the
exception raised by application code, not from a traceback.

Unhandled database and file-storage failures (``SQLAlchemyError``/``OSError``)
also return the JSON envelope with a generic 500 message; the real cause is
only written to the server logs.
"""
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

_STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "REQUEST_ENTITY_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_SERVER_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def error_code_for(status_code: int) -> str:
    return _STATUS_CODES.get(status_code, "ERROR")


def _error_body(status_code: int, message: str) -> dict[str, Any]:
    return {
        "error": {
            "code": error_code_for(status_code),
            "message": message,
        }
    }


def _internal_server_error() -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error",
            },
        },
    )


async def sqlalchemy_error_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Database failures become a generic JSON 500 (cause kept in logs)."""
    logger.error(
        "Unhandled database error on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return _internal_server_error()


async def os_error_handler(request: Request, exc: OSError) -> JSONResponse:
    """File-storage failures become a generic JSON 500 (cause kept in logs)."""
    logger.error(
        "Unhandled file/storage error on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return _internal_server_error()


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    detail = exc.detail
    content = {"detail": detail}
    content.update(_error_body(exc.status_code, str(detail)))
    return JSONResponse(
        status_code=exc.status_code, content=content, headers=exc.headers
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    content = {"detail": exc.errors()}
    content.update(_error_body(422, "Request validation failed"))
    return JSONResponse(status_code=422, content=content)


def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )
    application.add_exception_handler(
        SQLAlchemyError, sqlalchemy_error_handler
    )
    application.add_exception_handler(OSError, os_error_handler)