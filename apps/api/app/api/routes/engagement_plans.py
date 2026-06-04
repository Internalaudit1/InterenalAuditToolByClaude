from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.api.deps.common import get_list_query
from app.core.enums import EngagementDocumentType
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.db.uow import UnitOfWork
from app.models.engagement import EngagementDocument
from app.models.support import Attachment
from app.schemas.common import ListQuery, PaginatedResponse
from app.schemas.engagement import (
    EngagementDecisionRequest,
    EngagementDocumentResponse,
    EngagementPlanCreate,
    EngagementPlanPrefillResponse,
    EngagementPlanResponse,
    EngagementPlanUpdate,
    EngagementResourceCreate,
    EngagementResourceResponse,
    EngagementResourceUpdate,
    KickoffChecklistPatchRequest,
    KickoffChecklistItemResponse,
)
from app.services.engagement import engagement_service
from app.services.file_storage import file_storage

router = APIRouter(prefix="/engagement-plans", tags=["engagement plans"])


def _attachment_file_response(attachment: Attachment, *, inline: bool = False) -> FileResponse:
    path = Path(attachment.storage_path)
    if not path.exists():
        raise NotFoundException("Stored document file not found.")
    if inline:
        return FileResponse(
            path=str(path),
            media_type=attachment.content_type,
            headers={"Content-Disposition": f'inline; filename="{attachment.file_name}"'},
        )
    return FileResponse(path=str(path), filename=attachment.file_name, media_type=attachment.content_type)


@router.get("", response_model=PaginatedResponse[EngagementPlanResponse])
def list_engagement_plans(
    query: Annotated[ListQuery, Depends(get_list_query)],
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:view")),
    db: Session = Depends(get_db),
):
    return engagement_service.list(db, query, current_user)


@router.post("", response_model=EngagementPlanResponse)
def create_engagement_plan(
    payload: EngagementPlanCreate,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:manage")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return engagement_service.create(db, payload, current_user)


@router.get("/prefill/{audit_id}", response_model=EngagementPlanPrefillResponse)
def get_engagement_plan_prefill(
    audit_id: int,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:manage")),
    db: Session = Depends(get_db),
):
    return engagement_service.prefill_for_audit(db, audit_id, current_user)


@router.get("/{engagement_plan_id}", response_model=EngagementPlanResponse)
def get_engagement_plan(
    engagement_plan_id: int,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:view")),
    db: Session = Depends(get_db),
):
    return engagement_service.get(db, engagement_plan_id, current_user)


@router.patch("/{engagement_plan_id}", response_model=EngagementPlanResponse)
def update_engagement_plan(
    engagement_plan_id: int,
    payload: EngagementPlanUpdate,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:manage")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return engagement_service.update(db, engagement_plan_id, payload, current_user)


@router.post("/{engagement_plan_id}/submit", response_model=EngagementPlanResponse)
def submit_engagement_plan(
    engagement_plan_id: int,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:manage")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return engagement_service.submit(db, engagement_plan_id, current_user)


@router.post("/{engagement_plan_id}/approve", response_model=EngagementPlanResponse)
def approve_engagement_plan(
    engagement_plan_id: int,
    payload: EngagementDecisionRequest,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:approve")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return engagement_service.approve(db, engagement_plan_id, current_user, payload)


@router.post("/{engagement_plan_id}/reject", response_model=EngagementPlanResponse)
def reject_engagement_plan(
    engagement_plan_id: int,
    payload: EngagementDecisionRequest,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:approve")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return engagement_service.reject(db, engagement_plan_id, current_user, payload)


@router.get("/{engagement_plan_id}/kickoff-checklist", response_model=list[KickoffChecklistItemResponse])
def get_kickoff_checklist(
    engagement_plan_id: int,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:view")),
    db: Session = Depends(get_db),
):
    return engagement_service.list_checklist(db, engagement_plan_id, current_user)


@router.patch("/{engagement_plan_id}/kickoff-checklist", response_model=list[KickoffChecklistItemResponse])
def patch_kickoff_checklist(
    engagement_plan_id: int,
    payload: KickoffChecklistPatchRequest,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:manage")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return engagement_service.patch_checklist(db, engagement_plan_id, payload, current_user)


@router.get("/{engagement_plan_id}/resources", response_model=list[EngagementResourceResponse])
def list_resources(
    engagement_plan_id: int,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:view")),
    db: Session = Depends(get_db),
):
    return engagement_service.list_resources(db, engagement_plan_id, current_user)


@router.post("/{engagement_plan_id}/resources", response_model=EngagementResourceResponse)
def create_resource(
    engagement_plan_id: int,
    payload: EngagementResourceCreate,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:manage")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return engagement_service.add_resource(db, engagement_plan_id, payload, current_user)


@router.patch("/{engagement_plan_id}/resources/{resource_id}", response_model=EngagementResourceResponse)
def update_resource(
    engagement_plan_id: int,
    resource_id: int,
    payload: EngagementResourceUpdate,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:manage")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return engagement_service.update_resource(db, engagement_plan_id, resource_id, payload, current_user)


@router.get("/{engagement_plan_id}/documents", response_model=list[EngagementDocumentResponse])
def list_documents(
    engagement_plan_id: int,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:view")),
    db: Session = Depends(get_db),
):
    return engagement_service.list_documents(db, engagement_plan_id, current_user)


@router.get("/documents/{engagement_document_id}/download")
def download_document(
    engagement_document_id: int,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:view")),
    db: Session = Depends(get_db),
):
    document = db.scalar(
        select(EngagementDocument).where(
            EngagementDocument.id == engagement_document_id,
            EngagementDocument.is_deleted.is_(False),
        )
    )
    if not document:
        raise NotFoundException("Engagement document not found.")
    engagement_service.get(db, document.engagement_plan_id, current_user)
    attachment = db.scalar(
        select(Attachment).where(
            Attachment.id == document.document_id,
            Attachment.is_deleted.is_(False),
        )
    )
    if not attachment:
        raise NotFoundException("Attached engagement document file not found.")
    return _attachment_file_response(attachment)


@router.get("/documents/{engagement_document_id}/view")
def view_document(
    engagement_document_id: int,
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:view")),
    db: Session = Depends(get_db),
):
    document = db.scalar(
        select(EngagementDocument).where(
            EngagementDocument.id == engagement_document_id,
            EngagementDocument.is_deleted.is_(False),
        )
    )
    if not document:
        raise NotFoundException("Engagement document not found.")
    engagement_service.get(db, document.engagement_plan_id, current_user)
    attachment = db.scalar(
        select(Attachment).where(
            Attachment.id == document.document_id,
            Attachment.is_deleted.is_(False),
        )
    )
    if not attachment:
        raise NotFoundException("Attached engagement document file not found.")
    return _attachment_file_response(attachment, inline=True)


@router.post("/{engagement_plan_id}/documents", response_model=EngagementDocumentResponse)
async def upload_document(
    engagement_plan_id: int,
    document_type: EngagementDocumentType = Form(...),
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permissions("engagement_plans:manage")),
    db: Session = Depends(get_db),
):
    plan = engagement_service.prepare_document_upload(db, engagement_plan_id, current_user)
    audit_reference = plan.audit.audit_number if plan.audit else f"id-{plan.audit_id}"
    engagement_reference = plan.engagement_code or f"id-{plan.id}"
    stored = await file_storage.save_for_context(
        file,
        f"audit-{audit_reference}",
        "engagement-plans",
        engagement_reference,
        document_type.value,
    )
    with UnitOfWork(db):
        return engagement_service.add_document(
            db,
            engagement_plan_id=engagement_plan_id,
            document_type=document_type,
            file_name=file.filename or stored.stored_name,
            stored_name=stored.stored_name,
            content_type=file.content_type or "application/octet-stream",
            file_size=stored.size,
            storage_path=stored.storage_path,
            current_user=current_user,
        )
