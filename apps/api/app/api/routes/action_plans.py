from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.api.deps.common import get_list_query
from app.db.session import get_db
from app.models.support import Attachment
from app.schemas.action_plan import (
    ActionPlanCreate,
    ActionPlanRemarksRequest,
    ActionPlanResponse,
    ActionPlanResponseRequest,
    ActionPlanReviewRequest,
    ActionPlanReopenRequest,
    ActionPlanUpdate,
)
from app.schemas.common import BulkDeleteRequest, BulkDeleteResponse, ListQuery, MessageResponse, PaginatedResponse
from app.schemas.management_review import ManagementReviewCreate, ManagementReviewResponse
from app.services.action_plan import action_plan_service
from app.services.file_storage import file_storage
from app.services.management_review import management_review_service

router = APIRouter(prefix="/action-plans", tags=["action plans"])


def _management_review_response(review) -> ManagementReviewResponse:
    return ManagementReviewResponse(
        **{
            "id": review.id,
            "audit_id": review.audit_id,
            "action_plan_id": review.action_plan_id,
            "review_note": review.review_note,
            "review_decision": review.review_decision,
            "created_by_user_id": review.created_by_user_id,
            "created_by_user_name": review.created_by_user.full_name if review.created_by_user else review.created_by,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
            "created_by": review.created_by,
            "updated_by": review.updated_by,
            "is_deleted": review.is_deleted,
        }
    )


@router.get("", response_model=PaginatedResponse[ActionPlanResponse])
def list_action_plans(
    query: Annotated[ListQuery, Depends(get_list_query)],
    audit_id: int | None = Query(None),
    location_id: int | None = Query(None),
    auditor_status: str | None = Query(None),
    auditee_status: str | None = Query(None),
    _: CurrentUser = Depends(require_permissions("action_plans:view")),
    db: Session = Depends(get_db),
):
    filters = {}
    if audit_id:
        filters["audit_id"] = audit_id
    if location_id:
        filters["location_id"] = location_id
    if auditor_status:
        filters["auditor_status"] = auditor_status
    if auditee_status:
        filters["auditee_status"] = auditee_status
    query.filters = filters or None
    return action_plan_service.list(db, query)


@router.get("/summary")
def action_plan_summary(
    _: CurrentUser = Depends(require_permissions("action_plans:view")),
    db: Session = Depends(get_db),
):
    counts = action_plan_service.summary_counts(db)
    counts["due_soon"] = action_plan_service.due_soon_count(db)
    return counts


@router.get("/{action_plan_id}", response_model=ActionPlanResponse)
def get_action_plan(
    action_plan_id: int,
    _: CurrentUser = Depends(require_permissions("action_plans:view")),
    db: Session = Depends(get_db),
):
    return action_plan_service.get(db, action_plan_id)


@router.post("", response_model=ActionPlanResponse)
def create_action_plan(
    payload: ActionPlanCreate,
    current_user: CurrentUser = Depends(require_permissions("action_plans:create")),
    db: Session = Depends(get_db),
):
    entity = action_plan_service.create(db, payload, current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.put("/{action_plan_id}", response_model=ActionPlanResponse)
def update_action_plan(
    action_plan_id: int,
    payload: ActionPlanUpdate,
    current_user: CurrentUser = Depends(require_permissions("action_plans:create")),
    db: Session = Depends(get_db),
):
    entity = action_plan_service.update(db, action_plan_id, payload, current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.delete("/{action_plan_id}", response_model=MessageResponse)
def delete_action_plan(
    action_plan_id: int,
    current_user: CurrentUser = Depends(require_permissions("action_plans:delete")),
    db: Session = Depends(get_db),
):
    action_plan_service.delete(db, action_plan_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="Action plan deleted.")


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_action_plans(
    payload: BulkDeleteRequest,
    current_user: CurrentUser = Depends(require_permissions("action_plans:delete")),
    db: Session = Depends(get_db),
):
    response = action_plan_service.bulk_delete(db, payload.ids, current_user.full_name, current_user.id)
    db.commit()
    return response


@router.post("/{action_plan_id}/response", response_model=ActionPlanResponse)
def submit_response(
    action_plan_id: int,
    payload: ActionPlanResponseRequest,
    current_user: CurrentUser = Depends(require_permissions("action_plans:respond")),
    db: Session = Depends(get_db),
):
    entity = action_plan_service.submit_response(
        db,
        action_plan_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        role_codes=current_user.role_codes,
    )
    db.commit()
    return entity


@router.post("/{action_plan_id}/remarks", response_model=ActionPlanResponse)
def submit_remarks(
    action_plan_id: int,
    payload: ActionPlanRemarksRequest,
    current_user: CurrentUser = Depends(require_permissions("action_plans:respond")),
    db: Session = Depends(get_db),
):
    entity = action_plan_service.submit_remarks(
        db,
        action_plan_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        role_codes=current_user.role_codes,
    )
    db.commit()
    return entity


@router.post("/{action_plan_id}/review", response_model=ActionPlanResponse)
def review_action_plan(
    action_plan_id: int,
    payload: ActionPlanReviewRequest,
    current_user: CurrentUser = Depends(require_permissions("action_plans:review")),
    db: Session = Depends(get_db),
):
    entity = action_plan_service.review(
        db,
        action_plan_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        role_codes=current_user.role_codes,
    )
    db.commit()
    return entity


@router.get("/{action_plan_id}/management-reviews", response_model=list[ManagementReviewResponse])
def list_management_reviews(
    action_plan_id: int,
    _: CurrentUser = Depends(require_permissions("management_reviews:view")),
    db: Session = Depends(get_db),
):
    return [_management_review_response(review) for review in management_review_service.list_for_action_plan(db, action_plan_id)]


@router.post("/{action_plan_id}/management-reviews", response_model=ManagementReviewResponse)
def create_management_review(
    action_plan_id: int,
    payload: ManagementReviewCreate,
    current_user: CurrentUser = Depends(require_permissions("management_reviews:create")),
    db: Session = Depends(get_db),
):
    review = management_review_service.create_for_action_plan(db, action_plan_id, payload, current_user)
    db.commit()
    return _management_review_response(management_review_service.list_for_action_plan(db, action_plan_id)[0])


@router.post("/{action_plan_id}/reopen", response_model=ActionPlanResponse)
def reopen_action_plan(
    action_plan_id: int,
    payload: ActionPlanReopenRequest,
    current_user: CurrentUser = Depends(require_permissions("action_plans:review")),
    db: Session = Depends(get_db),
):
    entity = action_plan_service.reopen(
        db,
        action_plan_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        role_codes=current_user.role_codes,
    )
    db.commit()
    return entity


@router.post("/{action_plan_id}/attachments")
async def upload_attachment(
    action_plan_id: int,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permissions("action_plans:respond")),
    db: Session = Depends(get_db),
):
    stored_name, size = await file_storage.save(file)
    attachment = action_plan_service.attach_file(
        db,
        action_plan_id=action_plan_id,
        file_name=file.filename or stored_name,
        stored_name=stored_name,
        content_type=file.content_type or "application/octet-stream",
        file_size=size,
        storage_path=str(Path(file_storage.root) / stored_name),
        uploaded_by_user_id=current_user.id,
        actor_name=current_user.full_name,
    )
    db.commit()
    return attachment


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    _: CurrentUser = Depends(require_permissions("action_plans:view")),
    db: Session = Depends(get_db),
):
    attachment = db.scalar(select(Attachment).where(Attachment.id == attachment_id, Attachment.is_deleted.is_(False)))
    return FileResponse(path=attachment.storage_path, filename=attachment.file_name, media_type=attachment.content_type)
