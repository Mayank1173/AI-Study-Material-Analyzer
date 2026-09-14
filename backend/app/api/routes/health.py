from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.db.health import check_database_health

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Liveness check")
def liveness():
    """Liveness: the application process is running and can respond.

    This endpoint never touches the database and always returns 200 while the
    process is alive. Use it for "is the process up" monitoring.
    """
    return {"status": "healthy"}


@router.get("/database", summary="Database health check")
def database_health():
    """Database health: reports PostgreSQL connectivity.

    Returns 200 when the database answers a simple ``SELECT 1``, and 503 when
    it is unreachable. Use it to monitor the database dependency specifically.
    """
    if check_database_health():
        return {"status": "healthy", "database": "connected"}
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "unhealthy", "database": "unavailable"},
    )


@router.get("/ready", summary="Readiness check")
def readiness():
    """Readiness: the application is ready to serve requests.

    The only external dependency of this service is PostgreSQL, so readiness
    is equivalent to database availability: 200 when the database is reachable,
    503 otherwise. Use it to decide whether to route traffic to this instance.
    """
    if check_database_health():
        return {"status": "ready", "database": "connected"}
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not_ready", "database": "unavailable"},
    )