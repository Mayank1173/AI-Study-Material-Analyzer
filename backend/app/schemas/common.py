from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Predictable pagination envelope used by list endpoints.

    Example:
        {
          "items": [...],
          "page": 1,
          "page_size": 20,
          "total": 123,
          "total_pages": 7
        }
    """

    items: list[T]
    page: int
    page_size: int
    total: int
    total_pages: int