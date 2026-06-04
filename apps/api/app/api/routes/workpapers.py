from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.api.deps.common import get_list_query
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.db.uow import UnitOfWork
from app.models.support import Attachment
from app.models.workpaper import EvidenceRegister, WorkpaperVersion
from app.schemas.common import ListQuery, PaginatedResponse
from app.schemas.workpaper import (
    EvidenceDetailResponse,
    EvidenceLinkCreate,
    EvidenceResponse,
    WorkpaperCreate,
    WorkpaperDetailResponse,
    WorkpaperResponse,
    WorkpaperReviewRequest,
    WorkpaperSubmitReviewRequest,
    WorkpaperUpdate,
)
from app.services.file_storage import file_storage
from app.services.workpaper import workpaper_service

router = APIRouter(tags=["workpapers", "evidence"])


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


@router.get("/workpapers", response_model=PaginatedResponse[WorkpaperResponse])
def list_workpapers(
    query: Annotated[ListQuery, Depends(get_list_query)],
    audit_id: int | None = Query(None),
    activity_id: int | None = Query(None),
    status: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permissions("workpapers:view")),
    db: Session = Depends(get_db),
):
    return workpaper_service.list_workpapers(
        db,
        query,
        current_user,
        audit_id=audit_id,
        activity_id=activity_id,
        status=status,
    )


@router.post("/workpapers", response_model=WorkpaperDetailResponse)
def create_workpaper(
    payload: WorkpaperCreate,
    current_user: CurrentUser = Depends(require_permissions("workpapers:manage")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return workpaper_service.create_workpaper(db, payload, current_user)


@router.get("/workpapers/{workpaper_id}", response_model=WorkpaperDetailResponse)
def get_workpaper(
    workpaper_id: int,
    current_user: CurrentUser = Depends(require_permissions("workpapers:view")),
    db: Session = Depends(get_db),
):
    return workpaper_service.get_workpaper(db, workpaper_id, current_user)


@router.patch("/workpapers/{workpaper_id}", response_model=WorkpaperDetailResponse)
def update_workpaper(
    workpaper_id: int,
    payload: WorkpaperUpdate,
    current_user: CurrentUser = Depends(require_permissions("workpapers:manage")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return workpaper_service.update_workpaper(db, workpaper_id, payload, current_user)


@router.post("/workpapers/{workpaper_id}/versions", response_model=WorkpaperDetailResponse)
async def upload_workpaper_version(
    workpaper_id: int,
    change_summary: str | None = Form(None),
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permissions("workpapers:manage")),
    db: Session = Depends(get_db),
):
    workpaper, next_version_no = workpaper_service.prepare_version_upload(db, workpaper_id, current_user)
    audit_reference = workpaper.audit.audit_number if workpaper.audit else f"id-{workpaper.audit_id}"
    workpaper_reference = workpaper.workpaper_code or f"id-{workpaper.id}"
    stored = await file_storage.save_for_context(
        file,
        f"audit-{audit_reference}",
        "workpapers",
        workpaper_reference,
        f"version-{next_version_no:03d}",
    )
    storage_path = stored.storage_path
    checksum = hashlib.sha256(Path(storage_path).read_bytes()).hexdigest()
    with UnitOfWork(db):
        return workpaper_service.upload_version(
            db,
            workpaper_id=workpaper_id,
            file_name=file.filename or stored.stored_name,
            stored_name=stored.stored_name,
            content_type=file.content_type or "application/octet-stream",
            file_size=stored.size,
            storage_path=storage_path,
            checksum=checksum,
            change_summary=change_summary,
            current_user=current_user,
        )


@router.post("/workpapers/{workpaper_id}/submit-review", response_model=WorkpaperDetailResponse)
def submit_workpaper_review(
    workpaper_id: int,
    payload: WorkpaperSubmitReviewRequest,
    current_user: CurrentUser = Depends(require_permissions("workpapers:manage")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return workpaper_service.submit_for_review(db, workpaper_id, payload, current_user)


@router.post("/workpapers/{workpaper_id}/review", response_model=WorkpaperDetailResponse)
def review_workpaper(
    workpaper_id: int,
    payload: WorkpaperReviewRequest,
    current_user: CurrentUser = Depends(require_permissions("workpapers:review")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return workpaper_service.review_workpaper(db, workpaper_id, payload, current_user)


@router.get("/workpapers/versions/{version_id}/download")
def download_workpaper_version(
    version_id: int,
    _: CurrentUser = Depends(require_permissions("workpapers:view")),
    db: Session = Depends(get_db),
):
    version = db.scalar(
        select(WorkpaperVersion).where(
            WorkpaperVersion.id == version_id,
            WorkpaperVersion.is_deleted.is_(False),
        )
    )
    if not version:
        raise NotFoundException("Workpaper version not found.")
    attachment = db.scalar(
        select(Attachment).where(
            Attachment.id == version.document_id,
            Attachment.is_deleted.is_(False),
        )
    )
    if not attachment:
        raise NotFoundException("Attached version file not found.")
    return _attachment_file_response(attachment)


@router.get("/workpapers/versions/{version_id}/view")
def view_workpaper_version(
    version_id: int,
    _: CurrentUser = Depends(require_permissions("workpapers:view")),
    db: Session = Depends(get_db),
):
    version = db.scalar(
        select(WorkpaperVersion).where(
            WorkpaperVersion.id == version_id,
            WorkpaperVersion.is_deleted.is_(False),
        )
    )
    if not version:
        raise NotFoundException("Workpaper version not found.")
    attachment = db.scalar(
        select(Attachment).where(
            Attachment.id == version.document_id,
            Attachment.is_deleted.is_(False),
        )
    )
    if not attachment:
        raise NotFoundException("Attached version file not found.")
    return _attachment_file_response(attachment, inline=True)


@router.get("/evidence", response_model=PaginatedResponse[EvidenceResponse])
def list_evidence(
    query: Annotated[ListQuery, Depends(get_list_query)],
    audit_id: int | None = Query(None),
    activity_id: int | None = Query(None),
    linked_workpaper_id: int | None = Query(None),
    current_user: CurrentUser = Depends(require_permissions("evidence:view")),
    db: Session = Depends(get_db),
):
    return workpaper_service.list_evidence(
        db,
        query,
        current_user,
        audit_id=audit_id,
        activity_id=activity_id,
        linked_workpaper_id=linked_workpaper_id,
    )


@router.post("/evidence", response_model=EvidenceDetailResponse)
async def create_evidence(
    audit_id: int = Form(...),
    activity_id: int | None = Form(None),
    source_type: str = Form(...),
    source_name: str = Form(...),
    evidence_description: str | None = Form(None),
    confidentiality_level: str = Form(...),
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permissions("evidence:manage")),
    db: Session = Depends(get_db),
):
    audit = workpaper_service.prepare_evidence_upload(
        db,
        audit_id=audit_id,
        activity_id=activity_id,
        confidentiality_level=confidentiality_level,
        current_user=current_user,
    )
    stored = await file_storage.save_to_staging(file)
    with UnitOfWork(db):
        evidence = workpaper_service.create_evidence(
            db,
            audit_id=audit_id,
            activity_id=activity_id,
            source_type=source_type,
            source_name=source_name,
            evidence_description=evidence_description,
            confidentiality_level=confidentiality_level,
            file_name=file.filename or stored.stored_name,
            stored_name=stored.stored_name,
            content_type=file.content_type or "application/octet-stream",
            file_size=stored.size,
            storage_path=stored.storage_path,
            current_user=current_user,
        )
        attachment = db.scalar(
            select(Attachment).where(
                Attachment.id == evidence.document_id,
                Attachment.is_deleted.is_(False),
            )
        )
        if not attachment:
            raise NotFoundException("Evidence file not found.")
        evidence_reference = evidence.evidence_code or f"id-{evidence.id}"
        final_path = file_storage.move_to_context(
            stored.storage_path,
            f"audit-{audit.audit_number or audit.id}",
            "evidence",
            evidence_reference,
            stored_name=stored.stored_name,
        )
        attachment.storage_path = final_path
        attachment.updated_by = current_user.full_name
        attachment.updated_by_user_id = current_user.id
        db.flush()
        return workpaper_service.get_evidence(db, evidence.id, current_user)


@router.get("/evidence/{evidence_id}", response_model=EvidenceDetailResponse)
def get_evidence(
    evidence_id: int,
    current_user: CurrentUser = Depends(require_permissions("evidence:view")),
    db: Session = Depends(get_db),
):
    return workpaper_service.get_evidence(db, evidence_id, current_user)


@router.post("/evidence/{evidence_id}/link", response_model=EvidenceDetailResponse)
def link_evidence(
    evidence_id: int,
    payload: EvidenceLinkCreate,
    current_user: CurrentUser = Depends(require_permissions("evidence:manage")),
    db: Session = Depends(get_db),
):
    with UnitOfWork(db):
        return workpaper_service.link_evidence(db, evidence_id, payload, current_user)


@router.get("/evidence/{evidence_id}/download")
def download_evidence(
    evidence_id: int,
    _: CurrentUser = Depends(require_permissions("evidence:view")),
    db: Session = Depends(get_db),
):
    evidence = db.scalar(
        select(EvidenceRegister).where(
            EvidenceRegister.id == evidence_id,
            EvidenceRegister.is_deleted.is_(False),
        )
    )
    if not evidence:
        raise NotFoundException("Evidence not found.")
    attachment = db.scalar(
        select(Attachment).where(
            Attachment.id == evidence.document_id,
            Attachment.is_deleted.is_(False),
        )
    )
    if not attachment:
        raise NotFoundException("Evidence file not found.")
    return _attachment_file_response(attachment)


@router.get("/evidence/{evidence_id}/view")
def view_evidence(
    evidence_id: int,
    _: CurrentUser = Depends(require_permissions("evidence:view")),
    db: Session = Depends(get_db),
):
    evidence = db.scalar(
        select(EvidenceRegister).where(
            EvidenceRegister.id == evidence_id,
            EvidenceRegister.is_deleted.is_(False),
        )
    )
    if not evidence:
        raise NotFoundException("Evidence not found.")
    attachment = db.scalar(
        select(Attachment).where(
            Attachment.id == evidence.document_id,
            Attachment.is_deleted.is_(False),
        )
    )
    if not attachment:
        raise NotFoundException("Evidence file not found.")
    return _attachment_file_response(attachment, inline=True)
