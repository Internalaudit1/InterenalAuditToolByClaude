from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.api.deps.common import get_list_query
from app.db.session import get_db
from app.schemas.audit import AuditCompletionResponse, AuditCreate, AuditMembershipCreate, AuditMembershipResponse, AuditResponse, AuditUpdate
from app.schemas.common import BulkDeleteRequest, BulkDeleteResponse, ListQuery, MessageResponse, PaginatedResponse
from app.services.audit import audit_service

router = APIRouter(prefix="/audits", tags=["audits"])


@router.get("", response_model=PaginatedResponse[AuditResponse])
def list_audits(
    query: Annotated[ListQuery, Depends(get_list_query)],
    status: str | None = Query(None),
    quarter: str | None = Query(None),
    planned_flag: bool | None = Query(None),
    scope: str | None = Query(None, pattern="^(mine|team|all)$"),
    current_user: CurrentUser = Depends(require_permissions("audits:view")),
    db: Session = Depends(get_db),
):
    filters = {}
    if status:
        filters["status"] = status
    if quarter:
        filters["quarter"] = quarter
    if planned_flag is not None:
        filters["planned_flag"] = planned_flag
    query.filters = filters or None
    return audit_service.list_audits(db, query, current_user=current_user, scope=scope)


@router.get("/{audit_id}", response_model=AuditResponse)
def get_audit(
    audit_id: int,
    current_user: CurrentUser = Depends(require_permissions("audits:view")),
    db: Session = Depends(get_db),
):
    return audit_service.get_audit(db, audit_id, current_user)


@router.get("/{audit_id}/completion", response_model=AuditCompletionResponse)
def get_audit_completion(
    audit_id: int,
    current_user: CurrentUser = Depends(require_permissions("audit_activities:view")),
    db: Session = Depends(get_db),
):
    return audit_service.completion(db, audit_id, current_user)


@router.get("/{audit_id}/members", response_model=list[AuditMembershipResponse])
def list_audit_members(
    audit_id: int,
    current_user: CurrentUser = Depends(require_permissions("audit_memberships:view")),
    db: Session = Depends(get_db),
):
    return audit_service.list_members(db, audit_id, current_user)


@router.post("/{audit_id}/members", response_model=AuditMembershipResponse)
def add_audit_member(
    audit_id: int,
    payload: AuditMembershipCreate,
    current_user: CurrentUser = Depends(require_permissions("audit_memberships:manage")),
    db: Session = Depends(get_db),
):
    membership = audit_service.add_member(db, audit_id, payload, current_user.full_name, current_user.id)
    db.commit()
    return membership


@router.delete("/{audit_id}/members/{membership_id}", response_model=MessageResponse)
def remove_audit_member(
    audit_id: int,
    membership_id: int,
    current_user: CurrentUser = Depends(require_permissions("audit_memberships:manage")),
    db: Session = Depends(get_db),
):
    audit_service.remove_member(db, audit_id, membership_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="Audit membership removed.")


@router.post("", response_model=AuditResponse)
def create_audit(
    payload: AuditCreate,
    current_user: CurrentUser = Depends(require_permissions("audits:manage")),
    db: Session = Depends(get_db),
):
    entity = audit_service.create_audit(db, payload, current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.put("/{audit_id}", response_model=AuditResponse)
def update_audit(
    audit_id: int,
    payload: AuditUpdate,
    current_user: CurrentUser = Depends(require_permissions("audits:manage")),
    db: Session = Depends(get_db),
):
    entity = audit_service.update_audit(db, audit_id, payload, current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.delete("/{audit_id}", response_model=MessageResponse)
def delete_audit(
    audit_id: int,
    current_user: CurrentUser = Depends(require_permissions("audits:delete")),
    db: Session = Depends(get_db),
):
    audit_service.delete_audit(db, audit_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="Audit deleted.")


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_audits(
    payload: BulkDeleteRequest,
    current_user: CurrentUser = Depends(require_permissions("audits:delete")),
    db: Session = Depends(get_db),
):
    response = audit_service.bulk_delete_audits(db, payload.ids, current_user.full_name, current_user.id)
    db.commit()
    return response
