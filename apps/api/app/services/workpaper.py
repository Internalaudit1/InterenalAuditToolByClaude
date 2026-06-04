from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import CurrentUser
from app.core.enums import (
    ActivityAction,
    AttachmentOwnerType,
    AuditEventType,
    EvidenceConfidentialityLevel,
    WorkpaperReviewStatus,
    WorkpaperStatus,
)
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.models.audit import Audit, AuditActivity, Observation
from app.models.support import Attachment
from app.models.workpaper import EvidenceLink, EvidenceRegister, Workpaper, WorkpaperReview, WorkpaperVersion
from app.repositories.base import BaseRepository
from app.schemas.common import ListQuery, PaginationMeta, PaginatedResponse
from app.schemas.workpaper import (
    EvidenceLinkCreate,
    WorkpaperCreate,
    WorkpaperReviewRequest,
    WorkpaperSubmitReviewRequest,
    WorkpaperUpdate,
)
from app.services.activity_log import activity_log_service
from app.services.assignment_directory import assignment_directory_service
from app.services.audit_event import audit_event_service
from app.services.audit_scope import apply_audit_scope, assert_can_see_audit, has_global_audit_visibility
from app.services.authorization import apply_company_location_scope, ensure_same_company_location
from app.utils.serialization import model_to_dict


class WorkpaperService:
    workpaper_repo = BaseRepository(Workpaper)
    version_repo = BaseRepository(WorkpaperVersion)
    review_repo = BaseRepository(WorkpaperReview)
    attachment_repo = BaseRepository(Attachment)
    evidence_repo = BaseRepository(EvidenceRegister)
    evidence_link_repo = BaseRepository(EvidenceLink)

    review_transitions: dict[str, str] = {
        WorkpaperStatus.SUBMITTED_FOR_REVIEW.value: WorkpaperReviewStatus.REVIEWED.value,
        WorkpaperStatus.REVIEWED.value: WorkpaperReviewStatus.APPROVED.value,
        WorkpaperStatus.APPROVED.value: WorkpaperReviewStatus.LOCKED.value,
    }

    def _get_audit(self, db: Session, audit_id: int) -> Audit:
        audit = db.scalar(select(Audit).where(Audit.id == audit_id, Audit.is_deleted.is_(False)))
        if not audit:
            raise NotFoundException("Audit not found.")
        return audit

    def _validate_activity(self, db: Session, *, audit_id: int, activity_id: int | None) -> None:
        if activity_id is None:
            return
        exists = db.scalar(
            select(AuditActivity.id).where(
                AuditActivity.id == activity_id,
                AuditActivity.audit_id == audit_id,
                AuditActivity.is_deleted.is_(False),
            )
        )
        if not exists:
            raise ValidationException("Selected activity does not belong to this audit.")

    def _validate_observation(self, db: Session, *, audit_id: int, observation_id: int | None) -> None:
        if observation_id is None:
            return
        exists = db.scalar(
            select(Observation.id).where(
                Observation.id == observation_id,
                Observation.audit_id == audit_id,
                Observation.is_deleted.is_(False),
            )
        )
        if not exists:
            raise ValidationException("Selected observation does not belong to this audit.")

    def _validate_test_procedure_hook(self, test_procedure_id: int | None) -> None:
        if test_procedure_id is None:
            return
        if test_procedure_id <= 0:
            raise ValidationException("Test procedure reference must be a positive number when provided.")

    def _validate_people(self, db: Session, *, owner_user_id: int | None, reviewer_user_id: int | None) -> None:
        if owner_user_id:
            assignment_directory_service.validate_internal_user(db, owner_user_id, "Workpaper owner")
        if reviewer_user_id:
            assignment_directory_service.validate_internal_user(db, reviewer_user_id, "Workpaper reviewer")

    def _stamp_create(self, data: dict, current_user: CurrentUser) -> None:
        data["created_by"] = current_user.full_name
        data["updated_by"] = current_user.full_name
        data["created_by_user_id"] = current_user.id
        data["updated_by_user_id"] = current_user.id

    def _stamp_update(self, data: dict, current_user: CurrentUser) -> None:
        data["updated_by"] = current_user.full_name
        data["updated_by_user_id"] = current_user.id

    def _assert_can_review(self, workpaper: Workpaper, current_user: CurrentUser) -> None:
        if has_global_audit_visibility(current_user):
            return
        audit_owner_id = workpaper.audit.audit_owner_id if workpaper.audit else None
        if current_user.id not in {workpaper.reviewer_user_id, audit_owner_id}:
            raise ForbiddenException("Only the assigned reviewer or lead auditor can review this workpaper.")

    def list_workpapers(
        self,
        db: Session,
        query: ListQuery,
        current_user: CurrentUser,
        *,
        audit_id: int | None = None,
        activity_id: int | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[Workpaper]:
        stmt = select(Workpaper).join(Audit, Audit.id == Workpaper.audit_id).where(
            Workpaper.is_deleted.is_(False),
            Audit.is_deleted.is_(False),
        )
        stmt = apply_audit_scope(stmt, current_user, Audit)
        stmt = apply_company_location_scope(
            stmt,
            current_user,
            company_column=Workpaper.company_id,
            location_column=Workpaper.location_id,
        )
        if audit_id:
            stmt = stmt.where(Workpaper.audit_id == audit_id)
        if activity_id:
            stmt = stmt.where(Workpaper.activity_id == activity_id)
        if status:
            stmt = stmt.where(Workpaper.status == status)
        if query.search:
            stmt = stmt.where(
                or_(
                    Workpaper.workpaper_code.ilike(f"%{query.search}%"),
                    Workpaper.title.ilike(f"%{query.search}%"),
                    Workpaper.status.ilike(f"%{query.search}%"),
                )
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if query.sort_by and hasattr(Workpaper, query.sort_by):
            sort_column = getattr(Workpaper, query.sort_by)
            stmt = stmt.order_by(desc(sort_column) if query.sort_order == "desc" else asc(sort_column))
        else:
            stmt = stmt.order_by(desc(Workpaper.updated_at))
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        return PaginatedResponse(
            items=list(db.scalars(stmt).all()),
            meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total),
        )

    def get_workpaper(self, db: Session, workpaper_id: int, current_user: CurrentUser) -> Workpaper:
        stmt = (
            select(Workpaper)
            .options(
                joinedload(Workpaper.audit),
                joinedload(Workpaper.versions),
                joinedload(Workpaper.reviews),
            )
            .where(Workpaper.id == workpaper_id, Workpaper.is_deleted.is_(False))
        )
        workpaper = db.execute(stmt).unique().scalar_one_or_none()
        if not workpaper:
            raise NotFoundException("Workpaper not found.")
        assert_can_see_audit(db, workpaper.audit_id, current_user)
        linked_ids = list(
            db.scalars(
                select(EvidenceLink.evidence_id).where(
                    EvidenceLink.linked_module == "workpaper",
                    EvidenceLink.linked_record_id == workpaper.id,
                    EvidenceLink.is_deleted.is_(False),
                )
            ).all()
        )
        workpaper.linked_evidence_ids = linked_ids
        return workpaper

    def create_workpaper(self, db: Session, payload: WorkpaperCreate, current_user: CurrentUser) -> Workpaper:
        assert_can_see_audit(db, payload.audit_id, current_user)
        audit = self._get_audit(db, payload.audit_id)
        ensure_same_company_location(current_user=current_user, company_id=audit.company_id, location_id=audit.location_id)
        self._validate_activity(db, audit_id=audit.id, activity_id=payload.activity_id)
        self._validate_observation(db, audit_id=audit.id, observation_id=payload.observation_id)
        self._validate_test_procedure_hook(payload.test_procedure_id)
        data = payload.model_dump()
        data["company_id"] = audit.company_id
        data["location_id"] = audit.location_id
        data["owner_user_id"] = data.get("owner_user_id") or current_user.id
        self._validate_people(db, owner_user_id=data.get("owner_user_id"), reviewer_user_id=data.get("reviewer_user_id"))
        data["status"] = WorkpaperStatus.DRAFT.value
        data["current_version_no"] = 0
        self._stamp_create(data, current_user)
        workpaper = self.workpaper_repo.create(db, data)
        audit_event_service.record(
            db,
            audit=audit,
            event_type=AuditEventType.WORKPAPER_CREATED,
            event_title="Workpaper created",
            actor_name=current_user.full_name,
            actor_id=current_user.id,
            description=workpaper.title,
            payload={"workpaper_id": workpaper.id, "workpaper_code": workpaper.workpaper_code},
        )
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="workpapers",
            entity_type="workpaper",
            entity_id=str(workpaper.id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(workpaper),
        )
        return self.get_workpaper(db, workpaper.id, current_user)

    def update_workpaper(self, db: Session, workpaper_id: int, payload: WorkpaperUpdate, current_user: CurrentUser) -> Workpaper:
        workpaper = self.get_workpaper(db, workpaper_id, current_user)
        if workpaper.status == WorkpaperStatus.LOCKED.value:
            raise ValidationException("Locked workpapers cannot be edited.")
        before = model_to_dict(workpaper)
        data = payload.model_dump(exclude_none=True)
        self._validate_activity(db, audit_id=workpaper.audit_id, activity_id=data.get("activity_id", workpaper.activity_id))
        self._validate_observation(db, audit_id=workpaper.audit_id, observation_id=data.get("observation_id", workpaper.observation_id))
        self._validate_test_procedure_hook(data.get("test_procedure_id", workpaper.test_procedure_id))
        self._validate_people(
            db,
            owner_user_id=data.get("owner_user_id", workpaper.owner_user_id),
            reviewer_user_id=data.get("reviewer_user_id", workpaper.reviewer_user_id),
        )
        self._stamp_update(data, current_user)
        workpaper = self.workpaper_repo.update(db, workpaper, data)
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="workpapers",
            entity_type="workpaper",
            entity_id=str(workpaper.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=model_to_dict(workpaper),
        )
        return self.get_workpaper(db, workpaper.id, current_user)

    def prepare_version_upload(self, db: Session, workpaper_id: int, current_user: CurrentUser) -> tuple[Workpaper, int]:
        workpaper = self.get_workpaper(db, workpaper_id, current_user)
        if workpaper.status == WorkpaperStatus.LOCKED.value:
            raise ValidationException("Locked workpapers cannot receive new versions.")
        return workpaper, workpaper.current_version_no + 1

    def upload_version(
        self,
        db: Session,
        *,
        workpaper_id: int,
        file_name: str,
        stored_name: str,
        content_type: str,
        file_size: int,
        storage_path: str,
        checksum: str,
        change_summary: str | None,
        current_user: CurrentUser,
    ) -> Workpaper:
        workpaper = self.get_workpaper(db, workpaper_id, current_user)
        if workpaper.status == WorkpaperStatus.LOCKED.value:
            raise ValidationException("Locked workpapers cannot receive new versions.")
        before = model_to_dict(workpaper)
        attachment = Attachment(
            owner_type=AttachmentOwnerType.WORKPAPER_VERSION.value,
            owner_id=workpaper.id,
            file_name=file_name,
            stored_name=stored_name,
            content_type=content_type,
            file_size=file_size,
            storage_path=storage_path,
            uploaded_by_user_id=current_user.id,
            created_by=current_user.full_name,
            updated_by=current_user.full_name,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        db.add(attachment)
        db.flush()
        self.version_repo.create(
            db,
            {
                "workpaper_id": workpaper.id,
                "version_no": workpaper.current_version_no + 1,
                "document_id": attachment.id,
                "change_summary": change_summary,
                "uploaded_by_user_id": current_user.id,
                "hash_checksum": checksum,
                "created_by": current_user.full_name,
                "updated_by": current_user.full_name,
                "created_by_user_id": current_user.id,
                "updated_by_user_id": current_user.id,
            },
        )
        workpaper.current_version_no += 1
        workpaper.updated_by = current_user.full_name
        workpaper.updated_by_user_id = current_user.id
        if workpaper.status != WorkpaperStatus.DRAFT.value:
            workpaper.status = WorkpaperStatus.DRAFT.value
            workpaper.signoff_at = None
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="workpapers",
            entity_type="workpaper_version",
            entity_id=str(workpaper.id),
            action_type=ActivityAction.UPLOAD.value,
            old_values=before,
            new_values={"workpaper": model_to_dict(workpaper), "attachment_id": attachment.id, "checksum": checksum},
        )
        return self.get_workpaper(db, workpaper.id, current_user)

    def submit_for_review(
        self,
        db: Session,
        workpaper_id: int,
        payload: WorkpaperSubmitReviewRequest,
        current_user: CurrentUser,
    ) -> Workpaper:
        workpaper = self.get_workpaper(db, workpaper_id, current_user)
        if workpaper.status != WorkpaperStatus.DRAFT.value:
            raise ValidationException("Only draft workpapers can be submitted for review.")
        if workpaper.current_version_no <= 0:
            raise ValidationException("Upload at least one version before submitting for review.")
        before = model_to_dict(workpaper)
        workpaper.status = WorkpaperStatus.SUBMITTED_FOR_REVIEW.value
        workpaper.updated_by = current_user.full_name
        workpaper.updated_by_user_id = current_user.id
        db.flush()
        audit_event_service.record(
            db,
            audit=workpaper.audit,
            event_type=AuditEventType.WORKPAPER_SUBMITTED,
            event_title="Workpaper submitted for review",
            actor_name=current_user.full_name,
            actor_id=current_user.id,
            from_status=before.get("status"),
            to_status=workpaper.status,
            description=payload.comment,
            payload={"workpaper_id": workpaper.id, "workpaper_code": workpaper.workpaper_code},
        )
        if workpaper.reviewer_user_id:
            activity_log_service.notify(
                db,
                user_id=workpaper.reviewer_user_id,
                title="Workpaper submitted for review",
                message=f"{workpaper.workpaper_code} is ready for review.",
                actor_user_id=current_user.id,
                actor_name=current_user.full_name,
                payload={"workpaper_id": workpaper.id, "status": workpaper.status},
            )
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="workpapers",
            entity_type="workpaper",
            entity_id=str(workpaper.id),
            action_type=ActivityAction.STATUS_CHANGE.value,
            old_values=before,
            new_values={**model_to_dict(workpaper), "comment": payload.comment},
        )
        return self.get_workpaper(db, workpaper.id, current_user)

    def review_workpaper(self, db: Session, workpaper_id: int, payload: WorkpaperReviewRequest, current_user: CurrentUser) -> Workpaper:
        workpaper = self.get_workpaper(db, workpaper_id, current_user)
        self._assert_can_review(workpaper, current_user)
        expected_next = self.review_transitions.get(workpaper.status)
        if not expected_next:
            raise ValidationException("This workpaper is not ready for the requested review action.")
        if payload.review_status.value != expected_next:
            raise ValidationException(f"The next valid review action is {expected_next}.")
        before = model_to_dict(workpaper)
        workpaper.status = payload.review_status.value
        workpaper.updated_by = current_user.full_name
        workpaper.updated_by_user_id = current_user.id
        if payload.review_status in {WorkpaperReviewStatus.APPROVED, WorkpaperReviewStatus.LOCKED}:
            workpaper.signoff_at = datetime.now(UTC)
        self.review_repo.create(
            db,
            {
                "workpaper_id": workpaper.id,
                "reviewer_user_id": current_user.id,
                "review_status": payload.review_status.value,
                "review_comment": payload.review_comment,
                "reviewed_at": datetime.now(UTC),
                "created_by": current_user.full_name,
                "updated_by": current_user.full_name,
                "created_by_user_id": current_user.id,
                "updated_by_user_id": current_user.id,
            },
        )
        db.flush()
        event_type = {
            WorkpaperReviewStatus.REVIEWED: AuditEventType.WORKPAPER_REVIEWED,
            WorkpaperReviewStatus.APPROVED: AuditEventType.WORKPAPER_APPROVED,
            WorkpaperReviewStatus.LOCKED: AuditEventType.WORKPAPER_LOCKED,
        }[payload.review_status]
        event_title = {
            WorkpaperReviewStatus.REVIEWED: "Workpaper reviewed",
            WorkpaperReviewStatus.APPROVED: "Workpaper approved",
            WorkpaperReviewStatus.LOCKED: "Workpaper locked",
        }[payload.review_status]
        audit_event_service.record(
            db,
            audit=workpaper.audit,
            event_type=event_type,
            event_title=event_title,
            actor_name=current_user.full_name,
            actor_id=current_user.id,
            from_status=before.get("status"),
            to_status=workpaper.status,
            description=payload.review_comment,
            payload={"workpaper_id": workpaper.id, "workpaper_code": workpaper.workpaper_code},
        )
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="workpapers",
            entity_type="workpaper_review",
            entity_id=str(workpaper.id),
            action_type=ActivityAction.APPROVE.value if payload.review_status == WorkpaperReviewStatus.APPROVED else ActivityAction.REVIEW.value,
            old_values=before,
            new_values={**model_to_dict(workpaper), "review_comment": payload.review_comment},
        )
        return self.get_workpaper(db, workpaper.id, current_user)

    def list_evidence(
        self,
        db: Session,
        query: ListQuery,
        current_user: CurrentUser,
        *,
        audit_id: int | None = None,
        activity_id: int | None = None,
        linked_workpaper_id: int | None = None,
    ) -> PaginatedResponse[EvidenceRegister]:
        stmt = select(EvidenceRegister).join(Audit, Audit.id == EvidenceRegister.audit_id).where(
            EvidenceRegister.is_deleted.is_(False),
            Audit.is_deleted.is_(False),
        )
        stmt = apply_audit_scope(stmt, current_user, Audit)
        stmt = apply_company_location_scope(
            stmt,
            current_user,
            company_column=EvidenceRegister.company_id,
            location_column=EvidenceRegister.location_id,
        )
        if audit_id:
            stmt = stmt.where(EvidenceRegister.audit_id == audit_id)
        if activity_id:
            stmt = stmt.where(EvidenceRegister.activity_id == activity_id)
        if linked_workpaper_id:
            stmt = stmt.join(EvidenceLink, EvidenceLink.evidence_id == EvidenceRegister.id).where(
                EvidenceLink.linked_module == "workpaper",
                EvidenceLink.linked_record_id == linked_workpaper_id,
                EvidenceLink.is_deleted.is_(False),
            )
        if query.search:
            stmt = stmt.where(
                or_(
                    EvidenceRegister.evidence_code.ilike(f"%{query.search}%"),
                    EvidenceRegister.source_type.ilike(f"%{query.search}%"),
                    EvidenceRegister.source_name.ilike(f"%{query.search}%"),
                )
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if query.sort_by and hasattr(EvidenceRegister, query.sort_by):
            sort_column = getattr(EvidenceRegister, query.sort_by)
            stmt = stmt.order_by(desc(sort_column) if query.sort_order == "desc" else asc(sort_column))
        else:
            stmt = stmt.order_by(desc(EvidenceRegister.collected_at), desc(EvidenceRegister.updated_at))
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        return PaginatedResponse(
            items=list(db.scalars(stmt).all()),
            meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total),
        )

    def get_evidence(self, db: Session, evidence_id: int, current_user: CurrentUser) -> EvidenceRegister:
        evidence = db.scalar(
            select(EvidenceRegister)
            .options(joinedload(EvidenceRegister.links))
            .where(EvidenceRegister.id == evidence_id, EvidenceRegister.is_deleted.is_(False))
        )
        if not evidence:
            raise NotFoundException("Evidence record not found.")
        assert_can_see_audit(db, evidence.audit_id, current_user)
        return evidence

    def create_evidence(
        self,
        db: Session,
        *,
        audit_id: int,
        activity_id: int | None,
        source_type: str,
        source_name: str,
        evidence_description: str | None,
        confidentiality_level: str,
        file_name: str,
        stored_name: str,
        content_type: str,
        file_size: int,
        storage_path: str,
        current_user: CurrentUser,
    ) -> EvidenceRegister:
        assert_can_see_audit(db, audit_id, current_user)
        audit = self._get_audit(db, audit_id)
        ensure_same_company_location(current_user=current_user, company_id=audit.company_id, location_id=audit.location_id)
        self._validate_activity(db, audit_id=audit_id, activity_id=activity_id)
        if confidentiality_level not in {level.value for level in EvidenceConfidentialityLevel}:
            raise ValidationException("Invalid confidentiality level.")
        attachment = Attachment(
            owner_type=AttachmentOwnerType.EVIDENCE_REGISTER.value,
            owner_id=0,
            file_name=file_name,
            stored_name=stored_name,
            content_type=content_type,
            file_size=file_size,
            storage_path=storage_path,
            uploaded_by_user_id=current_user.id,
            created_by=current_user.full_name,
            updated_by=current_user.full_name,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        db.add(attachment)
        db.flush()
        evidence = self.evidence_repo.create(
            db,
            {
                "audit_id": audit.id,
                "company_id": audit.company_id,
                "location_id": audit.location_id,
                "activity_id": activity_id,
                "source_type": source_type,
                "source_name": source_name,
                "evidence_description": evidence_description,
                "document_id": attachment.id,
                "collected_by_user_id": current_user.id,
                "collected_at": datetime.now(UTC),
                "confidentiality_level": confidentiality_level,
                "created_by": current_user.full_name,
                "updated_by": current_user.full_name,
                "created_by_user_id": current_user.id,
                "updated_by_user_id": current_user.id,
            },
        )
        attachment.owner_id = evidence.id
        attachment.updated_by = current_user.full_name
        attachment.updated_by_user_id = current_user.id
        db.flush()
        audit_event_service.record(
            db,
            audit=audit,
            event_type=AuditEventType.EVIDENCE_REGISTERED,
            event_title="Evidence registered",
            actor_name=current_user.full_name,
            actor_id=current_user.id,
            description=evidence.source_name,
            payload={"evidence_id": evidence.id, "evidence_code": evidence.evidence_code},
        )
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="evidence",
            entity_type="evidence",
            entity_id=str(evidence.id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(evidence),
        )
        return self.get_evidence(db, evidence.id, current_user)

    def prepare_evidence_upload(
        self,
        db: Session,
        *,
        audit_id: int,
        activity_id: int | None,
        confidentiality_level: str,
        current_user: CurrentUser,
    ) -> Audit:
        assert_can_see_audit(db, audit_id, current_user)
        audit = self._get_audit(db, audit_id)
        ensure_same_company_location(current_user=current_user, company_id=audit.company_id, location_id=audit.location_id)
        self._validate_activity(db, audit_id=audit_id, activity_id=activity_id)
        if confidentiality_level not in {level.value for level in EvidenceConfidentialityLevel}:
            raise ValidationException("Invalid confidentiality level.")
        return audit

    def link_evidence(self, db: Session, evidence_id: int, payload: EvidenceLinkCreate, current_user: CurrentUser) -> EvidenceRegister:
        evidence = self.get_evidence(db, evidence_id, current_user)
        linked_module = payload.linked_module.strip().lower()
        if linked_module not in {"workpaper", "observation", "test_procedure"}:
            raise ValidationException("Evidence can only be linked to workpaper, observation, or test_procedure.")

        if linked_module == "workpaper":
            workpaper = db.scalar(
                select(Workpaper).where(
                    Workpaper.id == payload.linked_record_id,
                    Workpaper.audit_id == evidence.audit_id,
                    Workpaper.is_deleted.is_(False),
                )
            )
            if not workpaper:
                raise ValidationException("Selected workpaper does not belong to the same audit as the evidence.")
        elif linked_module == "observation":
            observation = db.scalar(
                select(Observation).where(
                    Observation.id == payload.linked_record_id,
                    Observation.audit_id == evidence.audit_id,
                    Observation.is_deleted.is_(False),
                )
            )
            if not observation:
                raise ValidationException("Selected observation does not belong to the same audit as the evidence.")
        elif payload.linked_record_id <= 0:
            raise ValidationException("Test procedure link must reference a positive record id.")

        existing = db.scalar(
            select(EvidenceLink).where(
                EvidenceLink.evidence_id == evidence.id,
                EvidenceLink.linked_module == linked_module,
                EvidenceLink.linked_record_id == payload.linked_record_id,
                EvidenceLink.is_deleted.is_(False),
            )
        )
        if existing:
            return self.get_evidence(db, evidence.id, current_user)

        link = self.evidence_link_repo.create(
            db,
            {
                "evidence_id": evidence.id,
                "linked_module": linked_module,
                "linked_record_id": payload.linked_record_id,
                "created_by": current_user.full_name,
                "updated_by": current_user.full_name,
                "created_by_user_id": current_user.id,
                "updated_by_user_id": current_user.id,
            },
        )
        audit_event_service.record(
            db,
            audit=evidence.audit,
            event_type=AuditEventType.EVIDENCE_LINKED,
            event_title="Evidence linked",
            actor_name=current_user.full_name,
            actor_id=current_user.id,
            description=f"Evidence linked to {linked_module}.",
            payload={"evidence_id": evidence.id, "evidence_link_id": link.id, "linked_module": linked_module, "linked_record_id": payload.linked_record_id},
        )
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="evidence",
            entity_type="evidence_link",
            entity_id=str(link.id),
            action_type=ActivityAction.ASSIGN.value,
            new_values=model_to_dict(link),
        )
        return self.get_evidence(db, evidence.id, current_user)


workpaper_service = WorkpaperService()
