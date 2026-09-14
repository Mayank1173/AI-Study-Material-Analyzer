"""Shared pagination and search helpers."""


def total_pages(total: int, page_size: int) -> int:
    """Number of pages for a given total and page size (0 when empty)."""
    if total <= 0:
        return 0
    return (total + page_size - 1) // page_size


def escape_like(value: str) -> str:
    """Escape LIKE wildcards so user search terms are matched literally."""
    return (
        value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )