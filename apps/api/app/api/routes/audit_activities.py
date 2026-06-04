from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.api.deps.common import get_list_query
from app.db.session import get_db
from app.schemas.audit_activity import (
    AuditActivityAssignRequest,
    AuditActivityCreate,
    AuditActivityResponse,
    AuditActivityStatusRequest,
    AuditActivityUpdate,
)
from app.schemas.common import ListQuery, PaginatedResponse
from app.services.audit_activity import audit_activity_service

router = APIRouter(tags=["audit activities"])


@router.get("/audits/{audit_id}/activities", response_model=PaginatedResponse[AuditActivityResponse])
def list_audit_activities(
    audit_id: int,
    query: Annotated[ListQuery, Depends(get_list_query)],
    current_user: CurrentUser = Depends(require_permissions("audit_activities:view")),
    db: Session = Depends(get_db),
):
    return audit_activity_service.list_for_audit(db, audit_id, query, current_user)


@router.post("/audits/{audit_id}/activities", response_model=AuditActivityResponse)
def create_audit_activity(
    audit_id: int,
    payload: AuditActivityCreate,
    current_user: CurrentUser = Depends(require_permissions("audit_activities:manage")),
    db: Session = Depends(get_db),
):
    entity = audit_activity_service.create(db, audit_id, payload, current_user)
    db.commit()
    return entity


@router.put("/audit-activities/{activity_id}", response_model=AuditActivityResponse)
def update_audit_activity(
    activity_id: int,
    payload: AuditActivityUpdate,
    current_user: CurrentUser = Depends(require_permissions("audit_activities:manage")),
    db: Session = Depends(get_db),
):
    entity = audit_activity_service.update(db, activity_id, payload, current_user)
    db.commit()
    return entity


@router.post("/audit-activities/{activity_id}/assign", response_model=AuditActivityResponse)
def assign_audit_activity(
    activity_id: int,
    payload: AuditActivityAssignRequest,
    current_user: CurrentUser = Depends(require_permissions("audit_activities:manage")),
    db: Session = Depends(get_db),
):
    entity = audit_activity_service.assign(db, activity_id, payload.assigned_to_user_id, current_user)
    db.commit()
    return entity


@router.post("/audit-activities/{activity_id}/status", response_model=AuditActivityResponse)
def change_audit_activity_status(
    activity_id: int,
    payload: AuditActivityStatusRequest,
    current_user: CurrentUser = Depends(require_permissions("audit_activities:manage")),
    db: Session = Depends(get_db),
):
    entity = audit_activity_service.change_status(db, activity_id, payload, current_user)
    db.commit()
    return entity


@router.get("/me/activities", response_model=PaginatedResponse[AuditActivityResponse])
def my_activities(
    query: Annotated[ListQuery, Depends(get_list_query)],
    current_user: CurrentUser = Depends(require_permissions("audit_activities:view")),
    db: Session = Depends(get_db),
):
    return audit_activity_service.my_activities(db, query, current_user)
