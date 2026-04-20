from __future__ import annotations

from fastapi import Query

from app.schemas.common import ListQuery


def get_list_query(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
) -> ListQuery:
    return ListQuery(page=page, page_size=page_size, search=search, sort_by=sort_by, sort_order=sort_order, filters=None)
