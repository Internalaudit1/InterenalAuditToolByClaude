from __future__ import annotations

from fastapi import Query, Request

from app.schemas.common import ListQuery


def _coerce_filter_value(raw: str) -> str | int | bool | None:
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    if raw.isdigit():
        try:
            return int(raw)
        except ValueError:
            return raw
    return raw


def get_list_query(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
) -> ListQuery:
    reserved = {"page", "page_size", "search", "sort_by", "sort_order"}
    filters = {
        key: _coerce_filter_value(value)
        for key, value in request.query_params.multi_items()
        if key not in reserved
    }
    return ListQuery(page=page, page_size=page_size, search=search, sort_by=sort_by, sort_order=sort_order, filters=filters or None)
