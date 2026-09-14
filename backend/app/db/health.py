from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_engine


def check_database_health() -> bool:
    """Return True when the database answers a simple query.

    Never raises: connectivity problems (including OS-level network errors)
    are reported as ``False`` so health/readiness endpoints can fail
    gracefully.
    """
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False