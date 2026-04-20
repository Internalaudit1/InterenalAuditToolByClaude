from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import ActionPlanStatus, ActivityAction, AttachmentOwnerType, RoleCode
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.models.action_plan import ActionPlan, ActionPlanRevision
from app.models.support import Attachment
from app.repositories.base import BaseRepository
from app.schemas.action_plan import (
    ActionPlanCreate,
    ActionPlanRemarksRequest,
    ActionPlanReopenRequest,
    ActionPlanResponseRequest,
    ActionPlanReviewRequest,
    ActionPlanUpdate,
)
from app.schemas.common import BlockedDeleteItem, BulkDeleteResponse, ListQuery, PaginationMeta, PaginatedResponse
from app.services.activity_log import activity_log_service
from app.utils.serialization import model_to_dict


class ActionPlanService:
    repo = BaseRepository(ActionPlan)
    revision_repo = BaseRepository(ActionPlanRevision)
    attachment_repo = BaseRepository(Attachment)
    generated_reference_fields = {"action_plan_id", "audit_number", "observation_number"}

    auditee_transitions: dict[str, set[str]] = {
        ActionPlanStatus.PENDING.value: {ActionPlanStatus.IN_PROGRESS.value},
        ActionPlanStatus.IN_PROGRESS.value: {ActionPlanStatus.UNDER_REVIEW.value},
        ActionPlanStatus.REOPENED.value: {ActionPlanStatus.IN_PROGRESS.value},
        ActionPlanStatus.UNDER_REVIEW.value: set(),
        ActionPlanStatus.COMPLETED.value: set(),
    }

    def _reject_generated_references(self, data: dict) -> None:
        blocked = sorted(field for field in self.generated_reference_fields if field in data)
        if blocked:
            raise ValidationException(f"Generated reference fields are backend-controlled and cannot be supplied: {', '.join(blocked)}.")

    auditor_transitions: dict[str, set[str]] = {
        ActionPlanStatus.PENDING.value: {
            ActionPlanStatus.IN_PROGRESS.value,
            ActionPlanStatus.UNDER_REVIEW.value,
            ActionPlanStatus.COMPLETED.value,
            ActionPlanStatus.REOPENED.value,
        },
        ActionPlanStatus.IN_PROGRESS.value: {
            ActionPlanStatus.UNDER_REVIEW.value,
            ActionPlanStatus.COMPLETED.value,
            ActionPlanStatus.REOPENED.value,
        },
        ActionPlanStatus.UNDER_REVIEW.value: {ActionPlanStatus.COMPLETED.value, ActionPlanStatus.REOPENED.value},
        ActionPlanStatus.REOPENED.value: {ActionPlanStatus.IN_PROGRESS.value},
        ActionPlanStatus.COMPLETED.value: set(),
    }

    def list(self, db: Session, query: ListQuery) -> PaginatedResponse[ActionPlan]:
        items, total = self.repo.list(
            db,
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            search_fields=["action_plan_id", "audit_number", "observation_heading", "auditor_status", "auditee_status"],
            filters=query.filters,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        return PaginatedResponse(items=items, meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def get(self, db: Session, action_plan_id: int) -> ActionPlan:
        stmt = (
            select(ActionPlan)
            .options(joinedload(ActionPlan.revisions))
            .where(ActionPlan.id == action_plan_id, ActionPlan.is_deleted.is_(False))
        )
        action_plan = db.execute(stmt).unique().scalar_one_or_none()
        if not action_plan:
            raise NotFoundException("Action plan not found.")
        return action_plan

    def create(self, db: Session, payload: ActionPlanCreate, actor_name: str, actor_id: int | None) -> ActionPlan:
        if payload.auditee_status != ActionPlanStatus.PENDING.value:
            raise ValidationException("Auditee status must start as 'Pending to be initiated'.")
        if payload.auditor_status not in {ActionPlanStatus.PENDING.value, ActionPlanStatus.IN_PROGRESS.value}:
            raise ValidationException("Auditor status must start in a pending or in-progress state.")
        data = payload.model_dump()
        self._reject_generated_references(data)
        data["created_by"] = actor_name
        data["updated_by"] = actor_name
        action_plan = self.repo.create(db, data)
        self._add_revision(
            db,
            action_plan=action_plan,
            revision_number=0,
            remarks=payload.management_response,
            revised_date=payload.revised_date,
            updated_by_user_id=actor_id,
            attachment_id=None,
        )
        activity_log_service.notify(
            db,
            user_id=action_plan.implementation_owner_user_id,
            title="New action plan assigned",
            message=f"Action plan {action_plan.action_plan_id} requires response.",
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="action_plans",
            entity_type="action_plan",
            entity_id=str(action_plan.id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(action_plan),
        )
        return self.get(db, action_plan.id)

    def update(self, db: Session, action_plan_id: int, payload: ActionPlanUpdate, actor_name: str, actor_id: int | None) -> ActionPlan:
        action_plan = self.get(db, action_plan_id)
        before = model_to_dict(action_plan)
        data = payload.model_dump(exclude_none=True)
        self._reject_generated_references(data)
        data["updated_by"] = actor_name
        action_plan = self.repo.update(db, action_plan, data)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="action_plans",
            entity_type="action_plan",
            entity_id=str(action_plan.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=model_to_dict(action_plan),
        )
        return self.get(db, action_plan.id)

    def submit_response(
        self,
        db: Session,
        action_plan_id: int,
        payload: ActionPlanResponseRequest,
        *,
        actor_id: int,
        actor_name: str,
        role_codes: list[str],
    ) -> ActionPlan:
        action_plan = self.get(db, action_plan_id)
        if RoleCode.AUDITEE.value in role_codes and RoleCode.SUPER_ADMIN.value not in role_codes:
            raise ForbiddenException("Auditee users can only update implementation remarks.")
        if RoleCode.SUPER_ADMIN.value not in role_codes and action_plan.implementation_owner_user_id != actor_id:
            raise ForbiddenException("Only the assigned auditee or an authorized admin can submit a response.")
        if payload.auditee_status not in self.auditee_transitions.get(action_plan.auditee_status, set()):
            raise ValidationException("Invalid auditee status transition.")
        before = model_to_dict(action_plan)
        action_plan.management_response = payload.management_response
        action_plan.agreed_action_plan = payload.agreed_action_plan
        action_plan.management_implementation_remarks = payload.management_implementation_remarks
        action_plan.auditee_status = payload.auditee_status
        action_plan.revised_date = payload.revised_date
        action_plan.last_response_at = datetime.now(UTC)
        action_plan.updated_by = actor_name
        db.flush()
        attachment_id = payload.attachment_ids[0] if payload.attachment_ids else None
        self._add_revision(
            db,
            action_plan=action_plan,
            revision_number=action_plan.revision_count,
            remarks=payload.management_implementation_remarks,
            revised_date=payload.revised_date,
            updated_by_user_id=actor_id,
            attachment_id=attachment_id,
        )
        activity_log_service.notify(
            db,
            user_id=action_plan.assigned_auditor_user_id,
            title="Action plan response submitted",
            message=f"{action_plan.action_plan_id} is ready for auditor review.",
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role="auditee",
            module="action_plans",
            entity_type="action_plan",
            entity_id=str(action_plan.id),
            action_type=ActivityAction.RESPOND.value,
            old_values=before,
            new_values=model_to_dict(action_plan),
        )
        return self.get(db, action_plan.id)

    def submit_remarks(
        self,
        db: Session,
        action_plan_id: int,
        payload: ActionPlanRemarksRequest,
        *,
        actor_id: int,
        actor_name: str,
        role_codes: list[str],
    ) -> ActionPlan:
        action_plan = self.get(db, action_plan_id)
        if RoleCode.SUPER_ADMIN.value not in role_codes and action_plan.implementation_owner_user_id != actor_id:
            raise ForbiddenException("Only the assigned auditee or an authorized admin can update implementation remarks.")
        before = model_to_dict(action_plan)
        action_plan.management_implementation_remarks = payload.management_implementation_remarks
        action_plan.revision_count += 1
        action_plan.updated_by = actor_name
        db.flush()
        self._add_revision(
            db,
            action_plan=action_plan,
            revision_number=action_plan.revision_count,
            remarks=payload.management_implementation_remarks,
            revised_date=action_plan.revised_date,
            updated_by_user_id=actor_id,
            attachment_id=None,
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role="auditee" if RoleCode.AUDITEE.value in role_codes else None,
            module="action_plans",
            entity_type="action_plan",
            entity_id=str(action_plan.id),
            action_type=ActivityAction.RESPOND.value,
            old_values=before,
            new_values={"management_implementation_remarks": action_plan.management_implementation_remarks, "revision_count": action_plan.revision_count},
        )
        return self.get(db, action_plan.id)

    def review(
        self,
        db: Session,
        action_plan_id: int,
        payload: ActionPlanReviewRequest,
        *,
        actor_id: int,
        actor_name: str,
        role_codes: list[str],
    ) -> ActionPlan:
        action_plan = self.get(db, action_plan_id)
        if RoleCode.SUPER_ADMIN.value not in role_codes and action_plan.assigned_auditor_user_id != actor_id:
            raise ForbiddenException("Only the assigned auditor or super admin can review an action plan.")
        if payload.auditor_status not in self.auditor_transitions.get(action_plan.auditor_status, set()):
            raise ValidationException("Invalid auditor status transition.")
        if payload.auditor_status == ActionPlanStatus.COMPLETED.value and (
            action_plan.auditee_status != ActionPlanStatus.UNDER_REVIEW.value or not action_plan.management_response
        ):
            raise ValidationException("Action plan cannot be completed until auditee response is under review with evidence.")
        before = model_to_dict(action_plan)
        action_plan.auditor_status = payload.auditor_status
        action_plan.auditor_implementation_remarks = payload.auditor_implementation_remarks
        action_plan.last_review_at = datetime.now(UTC)
        if payload.auditor_status == ActionPlanStatus.COMPLETED.value:
            action_plan.completed_at = datetime.now(UTC)
            action_plan.auditee_status = ActionPlanStatus.COMPLETED.value
        action_plan.updated_by = actor_name
        db.flush()
        activity_log_service.notify(
            db,
            user_id=action_plan.implementation_owner_user_id,
            title="Action plan reviewed",
            message=f"{action_plan.action_plan_id} status moved to {action_plan.auditor_status}.",
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role="auditor",
            module="action_plans",
            entity_type="action_plan",
            entity_id=str(action_plan.id),
            action_type=ActivityAction.REVIEW.value,
            old_values=before,
            new_values=model_to_dict(action_plan),
        )
        return self.get(db, action_plan.id)

    def reopen(
        self,
        db: Session,
        action_plan_id: int,
        payload: ActionPlanReopenRequest,
        *,
        actor_id: int,
        actor_name: str,
        role_codes: list[str],
    ) -> ActionPlan:
        action_plan = self.get(db, action_plan_id)
        if RoleCode.SUPER_ADMIN.value not in role_codes and action_plan.assigned_auditor_user_id != actor_id:
            raise ForbiddenException("Only the assigned auditor or super admin can reopen an action plan.")
        before = model_to_dict(action_plan)
        action_plan.auditor_status = ActionPlanStatus.REOPENED.value
        action_plan.auditee_status = ActionPlanStatus.REOPENED.value
        action_plan.auditor_implementation_remarks = payload.auditor_implementation_remarks
        action_plan.revised_date = payload.revised_date or date.today()
        action_plan.revision_count += 1
        action_plan.updated_by = actor_name
        db.flush()
        self._add_revision(
            db,
            action_plan=action_plan,
            revision_number=action_plan.revision_count,
            remarks=payload.reason,
            revised_date=action_plan.revised_date,
            updated_by_user_id=actor_id,
            attachment_id=None,
        )
        activity_log_service.notify(
            db,
            user_id=action_plan.implementation_owner_user_id,
            title="Action plan reopened",
            message=f"{action_plan.action_plan_id} was reopened with comments from the auditor.",
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role="auditor",
            module="action_plans",
            entity_type="action_plan",
            entity_id=str(action_plan.id),
            action_type=ActivityAction.STATUS_CHANGE.value,
            old_values=before,
            new_values=model_to_dict(action_plan),
        )
        return self.get(db, action_plan.id)

    def attach_file(
        self,
        db: Session,
        *,
        action_plan_id: int,
        file_name: str,
        stored_name: str,
        content_type: str,
        file_size: int,
        storage_path: str,
        uploaded_by_user_id: int | None,
        actor_name: str,
    ) -> Attachment:
        self.get(db, action_plan_id)
        attachment = Attachment(
            owner_type=AttachmentOwnerType.ACTION_PLAN.value,
            owner_id=action_plan_id,
            file_name=file_name,
            stored_name=stored_name,
            content_type=content_type,
            file_size=file_size,
            storage_path=storage_path,
            uploaded_by_user_id=uploaded_by_user_id,
            created_by=actor_name,
            updated_by=actor_name,
        )
        db.add(attachment)
        db.flush()
        db.refresh(attachment)
        return attachment

    def delete(self, db: Session, action_plan_id: int, actor_name: str, actor_id: int | None) -> None:
        action_plan = self.get(db, action_plan_id)
        before = model_to_dict(action_plan)
        attachment_ids = {
            attachment_id
            for attachment_id in db.scalars(
                select(Attachment.id).where(
                    Attachment.owner_type == AttachmentOwnerType.ACTION_PLAN.value,
                    Attachment.owner_id == action_plan.id,
                    Attachment.is_deleted.is_(False),
                )
            ).all()
        }
        attachment_ids.update(revision.file_attachment_id for revision in action_plan.revisions if revision.file_attachment_id)

        for revision in action_plan.revisions:
            if revision.is_deleted:
                continue
            self.revision_repo.soft_delete(db, revision, actor_name=actor_name)

        for attachment_id in attachment_ids:
            attachment = self.attachment_repo.get(db, attachment_id)
            if attachment:
                self.attachment_repo.soft_delete(db, attachment, actor_name=actor_name)

        self.repo.soft_delete(db, action_plan, actor_name=actor_name)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="action_plans",
            entity_type="action_plan",
            entity_id=str(action_plan.id),
            action_type=ActivityAction.DELETE.value,
            old_values=before,
            new_values={"is_deleted": True, "deleted_revision_count": len(action_plan.revisions), "deleted_attachment_ids": sorted(attachment_ids)},
        )

    def bulk_delete(self, db: Session, ids: list[int], actor_name: str, actor_id: int | None) -> BulkDeleteResponse:
        deleted_ids: list[int] = []
        blocked: list[BlockedDeleteItem] = []
        for action_plan_id in ids:
            try:
                self.delete(db, action_plan_id, actor_name, actor_id)
                deleted_ids.append(action_plan_id)
            except NotFoundException as exc:
                blocked.append(BlockedDeleteItem(id=action_plan_id, reason=str(exc.detail)))
        response = BulkDeleteResponse(
            deleted_ids=deleted_ids,
            blocked=blocked,
            message=(
                f"Deleted {len(deleted_ids)} record(s)." if deleted_ids and not blocked else
                f"Deleted {len(deleted_ids)} record(s); {len(blocked)} record(s) could not be deleted." if deleted_ids else
                "No records were deleted."
            ),
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="action_plans",
            entity_type="action_plan",
            entity_id="bulk",
            action_type=ActivityAction.DELETE.value,
            new_values=response.model_dump(),
        )
        return response

    def summary_counts(self, db: Session) -> dict[str, int]:
        stmt = select(
            func.count(ActionPlan.id).label("all_actions"),
            func.sum(case((ActionPlan.auditor_status == ActionPlanStatus.IN_PROGRESS.value, 1), else_=0)).label("in_progress"),
            func.sum(case((ActionPlan.auditor_status == ActionPlanStatus.PENDING.value, 1), else_=0)).label("pending"),
            func.sum(case((ActionPlan.auditor_status == ActionPlanStatus.COMPLETED.value, 1), else_=0)).label("completed"),
            func.sum(
                case(
                    (
                        and_(
                            ActionPlan.agreed_timeline < date.today(),
                            ActionPlan.auditor_status != ActionPlanStatus.COMPLETED.value,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("overdue"),
        )
        row = db.execute(stmt).one()
        return {
            "all": row.all_actions or 0,
            "in_progress": row.in_progress or 0,
            "pending": row.pending or 0,
            "completed": row.completed or 0,
            "overdue": row.overdue or 0,
        }

    def due_soon_count(self, db: Session) -> int:
        due_limit = date.today() + timedelta(days=7)
        return (
            db.scalar(
                select(func.count(ActionPlan.id)).where(
                    and_(
                        ActionPlan.agreed_timeline >= date.today(),
                        ActionPlan.agreed_timeline <= due_limit,
                        ActionPlan.auditor_status != ActionPlanStatus.COMPLETED.value,
                    )
                )
            )
            or 0
        )

    def _add_revision(
        self,
        db: Session,
        *,
        action_plan: ActionPlan,
        revision_number: int,
        remarks: str | None,
        revised_date: date | None,
        updated_by_user_id: int | None,
        attachment_id: int | None,
    ) -> ActionPlanRevision:
        revision = ActionPlanRevision(
            action_plan_id=action_plan.id,
            revision_number=revision_number,
            management_implementation_remarks=remarks,
            revised_date=revised_date,
            file_attachment_id=attachment_id,
            updated_by_user_id=updated_by_user_id,
            status_snapshot={"auditor_status": action_plan.auditor_status, "auditee_status": action_plan.auditee_status},
            created_by=action_plan.updated_by,
            updated_by=action_plan.updated_by,
        )
        db.add(revision)
        db.flush()
        return revision


action_plan_service = ActionPlanService()
