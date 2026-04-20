from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.api.deps.common import get_list_query
from app.db.session import get_db
from app.schemas.common import BulkDeleteRequest, BulkDeleteResponse, ListQuery, MessageResponse, PaginatedResponse
from app.schemas.master import MasterRecordCreate, MasterRecordResponse, MasterRecordUpdate
from app.services.master import master_service

router = APIRouter(prefix="/master", tags=["master data"])


@router.get("/{resource}", response_model=PaginatedResponse[MasterRecordResponse])
def list_master_records(
    resource: str,
    query: Annotated[ListQuery, Depends(get_list_query)],
    _: CurrentUser = Depends(require_permissions("masters:view")),
    db: Session = Depends(get_db),
):
    return master_service.list(db, resource, query)


@router.post("/{resource}", response_model=MasterRecordResponse)
def create_master_record(
    resource: str,
    payload: MasterRecordCreate,
    current_user: CurrentUser = Depends(require_permissions("masters:manage")),
    db: Session = Depends(get_db),
):
    entity = master_service.create(db, resource, payload, current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.put("/{resource}/{entity_id}", response_model=MasterRecordResponse)
def update_master_record(
    resource: str,
    entity_id: int,
    payload: MasterRecordUpdate,
    current_user: CurrentUser = Depends(require_permissions("masters:manage")),
    db: Session = Depends(get_db),
):
    entity = master_service.update(db, resource, entity_id, payload, current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.delete("/{resource}/{entity_id}", response_model=MessageResponse)
def delete_master_record(
    resource: str,
    entity_id: int,
    current_user: CurrentUser = Depends(require_permissions("masters:delete")),
    db: Session = Depends(get_db),
):
    master_service.delete(db, resource, entity_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="Master record deleted.")


@router.post("/{resource}/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_master_records(
    resource: str,
    payload: BulkDeleteRequest,
    current_user: CurrentUser = Depends(require_permissions("masters:delete")),
    db: Session = Depends(get_db),
):
    response = master_service.bulk_delete(db, resource, payload.ids, current_user.full_name, current_user.id)
    db.commit()
    return response
