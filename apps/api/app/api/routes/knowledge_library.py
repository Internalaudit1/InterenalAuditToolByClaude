from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.api.deps.common import get_list_query
from app.db.session import get_db
from app.schemas.common import BulkDeleteRequest, BulkDeleteResponse, ListQuery, MessageResponse, PaginatedResponse
from app.schemas.library import KnowledgeLibraryItemCreate, KnowledgeLibraryItemResponse, KnowledgeLibraryItemUpdate
from app.services.library import library_service

router = APIRouter(prefix="/knowledge-library", tags=["knowledge library"])


@router.get("", response_model=PaginatedResponse[KnowledgeLibraryItemResponse])
def list_library_items(
    query: Annotated[ListQuery, Depends(get_list_query)],
    item_type: str | None = Query(None),
    category: str | None = Query(None),
    _: CurrentUser = Depends(require_permissions("library:view")),
    db: Session = Depends(get_db),
):
    filters = {}
    if item_type:
        filters["item_type"] = item_type
    if category:
        filters["category"] = category
    query.filters = filters or None
    return library_service.list(db, query)


@router.post("", response_model=KnowledgeLibraryItemResponse)
def create_library_item(
    payload: KnowledgeLibraryItemCreate,
    current_user: CurrentUser = Depends(require_permissions("library:manage")),
    db: Session = Depends(get_db),
):
    entity = library_service.create(db, payload, current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.put("/{item_id}", response_model=KnowledgeLibraryItemResponse)
def update_library_item(
    item_id: int,
    payload: KnowledgeLibraryItemUpdate,
    current_user: CurrentUser = Depends(require_permissions("library:manage")),
    db: Session = Depends(get_db),
):
    entity = library_service.update(db, item_id, payload, current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.delete("/{item_id}", response_model=MessageResponse)
def delete_library_item(
    item_id: int,
    current_user: CurrentUser = Depends(require_permissions("library:delete")),
    db: Session = Depends(get_db),
):
    library_service.delete(db, item_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="Knowledge library item deleted.")


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_library_items(
    payload: BulkDeleteRequest,
    current_user: CurrentUser = Depends(require_permissions("library:delete")),
    db: Session = Depends(get_db),
):
    response = library_service.bulk_delete(db, payload.ids, current_user.full_name, current_user.id)
    db.commit()
    return response
