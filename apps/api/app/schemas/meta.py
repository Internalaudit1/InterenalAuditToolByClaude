from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.common import PaginationMeta


class MetaForeignKeyResponse(BaseModel):
    references_table: str
    references_column: str


class MetaLookupResponse(BaseModel):
    endpoint: str
    value_field: str
    label_field: str
    display_field: str
    frontend_mode: str


class MetaTableResponse(BaseModel):
    table_name: str
    display_label: str
    category: str
    system_table: bool
    has_business_route: bool
    frontend_mode: str
    endpoint: str | None = None


class MetaColumnResponse(BaseModel):
    name: str
    ordinal_position: int
    data_type: str
    nullable: bool
    primary_key: bool
    foreign_key: MetaForeignKeyResponse | None = None
    default: str | None = None
    suggested_display_label: str
    editable: bool
    system_managed: bool
    hidden_by_default: bool
    input_type: str
    lookup: MetaLookupResponse | None = None


class MetaRelationshipResponse(BaseModel):
    direction: str
    constraint_name: str | None = None
    local_column: str
    related_table: str
    related_column: str


class MetaRowsResponse(BaseModel):
    items: list[dict[str, Any]]
    meta: PaginationMeta
