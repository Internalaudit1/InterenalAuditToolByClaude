from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int = 1
    page_size: int = 10
    total: int = 0


class PaginatedResponse(GenericModel, Generic[T]):
    items: list[T]
    meta: PaginationMeta


class ListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    search: str | None = None
    sort_by: str | None = None
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")
    filters: dict[str, str | int | bool | None] | None = None


class MessageResponse(BaseModel):
    message: str


class BulkDeleteRequest(BaseModel):
    ids: list[int] = Field(default_factory=list, min_length=1)


class BlockedDeleteItem(BaseModel):
    id: int
    reason: str


class BulkDeleteResponse(BaseModel):
    deleted_ids: list[int] = Field(default_factory=list)
    blocked: list[BlockedDeleteItem] = Field(default_factory=list)
    message: str
