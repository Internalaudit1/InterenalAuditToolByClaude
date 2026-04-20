from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, get_current_user
from app.api.deps.common import get_list_query
from app.db.session import get_db
from app.schemas.common import ListQuery
from app.schemas.meta import MetaColumnResponse, MetaRelationshipResponse, MetaRowsResponse, MetaTableResponse
from app.services.meta import meta_service

router = APIRouter(prefix="/meta", tags=["metadata"])


@router.get("/tables", response_model=list[MetaTableResponse])
def list_meta_tables(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return meta_service.list_tables(db, permissions=current_user.permissions, role_codes=current_user.role_codes)


@router.get("/tables/{table_name}/columns", response_model=list[MetaColumnResponse])
def list_meta_columns(
    table_name: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return meta_service.table_columns(db, table_name, permissions=current_user.permissions, role_codes=current_user.role_codes)


@router.get("/tables/{table_name}/relationships", response_model=list[MetaRelationshipResponse])
def list_meta_relationships(
    table_name: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return meta_service.table_relationships(db, table_name, permissions=current_user.permissions, role_codes=current_user.role_codes)


@router.get("/tables/{table_name}/rows", response_model=MetaRowsResponse)
def list_meta_rows(
    table_name: str,
    request: Request,
    query: Annotated[ListQuery, Depends(get_list_query)],
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw_filters = {key: value for key, value in request.query_params.items() if key not in {"page", "page_size", "search", "sort_by", "sort_order"}}
    return meta_service.list_rows(
        db,
        table_name,
        query,
        raw_filters,
        permissions=current_user.permissions,
        role_codes=current_user.role_codes,
    )
