from __future__ import annotations

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser
from app.core.enums import ActivityAction, AuditActivityStatus, RoleCode
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.models.audit import AuditActivity
from app.repositories.base import BaseRepository
from app.schemas.audit_activity import AuditActivityCreate, AuditActivityStatusRequest, AuditActivityUpdate
from app.schemas.common import ListQuery, PaginationMeta, PaginatedResponse
from app.services.activity_log import activity_log_service
from app.services.assignment_directory import assignment_directory_service
from app.services.audit_scope import assert_can_see_audit, membership_audit_ids_stmt
from app.utils.serialization import model_to_dict


class AuditActivityService:
    repo = BaseRepository(AuditActivity)
    valid_statuses = {status.value for status in AuditActivityStatus}

    def list_for_audit(self, db: Session, audit_id: int, query: ListQuery, current_user: CurrentUser) -> PaginatedResponse[AuditActivity]:
        assert_can_see_audit(db, audit_id, current_user)
        stmt = select(AuditActivity).where(AuditActivity.audit_id == audit_id, AuditActivity.is_deleted.is_(False))
        if query.search:
            stmt = stmt.where(or_(AuditActivity.title.ilike(f"%{query.search}%"), AuditActivity.status.ilike(f"%{query.search}%")))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if query.sort_by and hasattr(AuditActivity, query.sort_by):
            sort_column = getattr(AuditActivity, query.sort_by)
            stmt = stmt.order_by(desc(sort_column) if query.sort_order == "desc" else asc(sort_column))
        else:
            stmt = stmt.order_by(desc(AuditActivity.updated_at))
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        return PaginatedResponse(items=list(db.scalars(stmt).all()), meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def my_activities(self, db: Session, query: ListQuery, current_user: CurrentUser) -> PaginatedResponse[AuditActivity]:
        stmt = select(AuditActivity).where(
            AuditActivity.is_deleted.is_(False),
            (AuditActivity.assigned_to_user_id == current_user.id) | (AuditActivity.audit_id.in_(membership_audit_ids_stmt(current_user))),
        )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.order_by(desc(AuditActivity.updated_at)).offset((query.page - 1) * query.page_size).limit(query.page_size)
        return PaginatedResponse(items=list(db.scalars(stmt).all()), meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def get(self, db: Session, activity_id: int, current_user: CurrentUser) -> AuditActivity:
        activity = self.repo.get(db, activity_id)
        if not activity:
            raise NotFoundException("Audit activity not found.")
        assert_can_see_audit(db, activity.audit_id, current_user)
        return activity

    def create(self, db: Session, audit_id: int, payload: AuditActivityCreate, current_user: CurrentUser) -> AuditActivity:
        assert_can_see_audit(db, audit_id, current_user)
        if payload.status not in self.valid_statuses:
            raise ValidationException("Invalid activity status.")
        if payload.assigned_to_user_id:
            assignment_directory_service.validate_internal_user(db, payload.assigned_to_user_id, "Assigned auditor")
        data = payload.model_dump()
        data["audit_id"] = audit_id
        data["created_by"] = current_user.full_name
        data["updated_by"] = current_user.full_name
        activity = self.repo.create(db, data)
        if activity.assigned_to_user_id:
            activity_log_service.notify(db, user_id=activity.assigned_to_user_id, title="Audit activity assigned", message=f"Activity {activity.title} has been assigned to you.")
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="audit_activities",
            entity_type="audit_activity",
            entity_id=str(activity.id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(activity),
        )
        return activity

    def update(self, db: Session, activity_id: int, payload: AuditActivityUpdate, current_user: CurrentUser) -> AuditActivity:
        activity = self.get(db, activity_id, current_user)
        data = payload.model_dump(exclude_none=True)
        if "status" in data and data["status"] not in self.valid_statuses:
            raise ValidationException("Invalid activity status.")
        if "assigned_to_user_id" in data and data["assigned_to_user_id"]:
            assignment_directory_service.validate_internal_user(db, data["assigned_to_user_id"], "Assigned auditor")
        if RoleCode.AUDITEE.value in current_user.role_codes:
            raise ForbiddenException("Auditees cannot update audit activities.")
        before = model_to_dict(activity)
        data["updated_by"] = current_user.full_name
        activity = self.repo.update(db, activity, data)
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="audit_activities",
            entity_type="audit_activity",
            entity_id=str(activity.id),
            action_type=ActivityAction.UPDATE.value if "status" not in data else ActivityAction.STATUS_CHANGE.value,
            old_values=before,
            new_values=model_to_dict(activity),
        )
        return activity

    def assign(self, db: Session, activity_id: int, assigned_to_user_id: int | None, current_user: CurrentUser) -> AuditActivity:
        activity = self.get(db, activity_id, current_user)
        if assigned_to_user_id:
            assignment_directory_service.validate_internal_user(db, assigned_to_user_id, "Assigned auditor")
        before = model_to_dict(activity)
        activity.assigned_to_user_id = assigned_to_user_id
        activity.updated_by = current_user.full_name
        db.flush()
        if assigned_to_user_id:
            activity_log_service.notify(db, user_id=assigned_to_user_id, title="Audit activity assigned", message=f"Activity {activity.title} has been assigned to you.")
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="audit_activities",
            entity_type="audit_activity",
            entity_id=str(activity.id),
            action_type=ActivityAction.ASSIGN.value,
            old_values=before,
            new_values=model_to_dict(activity),
        )
        return activity

    def change_status(self, db: Session, activity_id: int, payload: AuditActivityStatusRequest, current_user: CurrentUser) -> AuditActivity:
        if payload.status not in self.valid_statuses:
            raise ValidationException("Invalid activity status.")
        activity = self.get(db, activity_id, current_user)
        before = model_to_dict(activity)
        activity.status = payload.status
        if payload.remarks is not None:
            activity.remarks = payload.remarks
        activity.updated_by = current_user.full_name
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="audit_activities",
            entity_type="audit_activity",
            entity_id=str(activity.id),
            action_type=ActivityAction.STATUS_CHANGE.value,
            old_values=before,
            new_values=model_to_dict(activity),
        )
        return activity


audit_activity_service = AuditActivityService()
