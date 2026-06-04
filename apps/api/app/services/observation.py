from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser
from app.core.enums import ActionPlanStatus, ActivityAction, ObservationStatus, RoleCode
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.models.action_plan import ActionPlan
from app.models.audit import Audit, AuditActivity, Observation
from app.repositories.base import BaseRepository
from app.schemas.common import ListQuery, PaginationMeta, PaginatedResponse
from app.schemas.observation import (
    ObservationConvertRequest,
    ObservationCreate,
    ObservationDispositionRequest,
    ObservationIssueRequest,
    ObservationResponseRequest,
    ObservationUpdate,
)
from app.services.activity_log import activity_log_service
from app.services.action_plan import action_plan_service
from app.services.assignment_directory import assignment_directory_service
from app.services.audit_scope import assert_can_see_audit, has_global_audit_visibility, membership_audit_ids_stmt
from app.utils.serialization import model_to_dict


class ObservationService:
    repo = BaseRepository(Observation)

    def list_for_audit(self, db: Session, audit_id: int, query: ListQuery, current_user: CurrentUser) -> PaginatedResponse[Observation]:
        assert_can_see_audit(db, audit_id, current_user)
        stmt = select(Observation).where(Observation.audit_id == audit_id, Observation.is_deleted.is_(False))
        if RoleCode.AUDITEE.value in current_user.role_codes and not has_global_audit_visibility(current_user):
            stmt = stmt.where(Observation.auditee_user_id == current_user.id)
        if query.search:
            stmt = stmt.where(or_(Observation.observation_number.ilike(f"%{query.search}%"), Observation.heading.ilike(f"%{query.search}%"), Observation.status.ilike(f"%{query.search}%")))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if query.sort_by and hasattr(Observation, query.sort_by):
            sort_column = getattr(Observation, query.sort_by)
            stmt = stmt.order_by(desc(sort_column) if query.sort_order == "desc" else asc(sort_column))
        else:
            stmt = stmt.order_by(desc(Observation.updated_at))
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        return PaginatedResponse(items=list(db.scalars(stmt).all()), meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def my_observations(self, db: Session, query: ListQuery, current_user: CurrentUser) -> PaginatedResponse[Observation]:
        stmt = select(Observation).where(Observation.is_deleted.is_(False))
        if RoleCode.AUDITEE.value in current_user.role_codes and not has_global_audit_visibility(current_user):
            stmt = stmt.where(Observation.auditee_user_id == current_user.id)
        elif not has_global_audit_visibility(current_user):
            stmt = stmt.where(Observation.audit_id.in_(membership_audit_ids_stmt(current_user)))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.order_by(desc(Observation.updated_at)).offset((query.page - 1) * query.page_size).limit(query.page_size)
        return PaginatedResponse(items=list(db.scalars(stmt).all()), meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def get(self, db: Session, observation_id: int, current_user: CurrentUser) -> Observation:
        observation = self.repo.get(db, observation_id)
        if not observation:
            raise NotFoundException("Observation not found.")
        if RoleCode.AUDITEE.value in current_user.role_codes and not has_global_audit_visibility(current_user):
            if observation.auditee_user_id != current_user.id:
                raise NotFoundException("Observation not found.")
        else:
            assert_can_see_audit(db, observation.audit_id, current_user)
        return observation

    def _validate_activity(self, db: Session, audit_id: int, activity_id: int | None) -> None:
        if activity_id is None:
            return
        exists = db.scalar(select(AuditActivity.id).where(AuditActivity.id == activity_id, AuditActivity.audit_id == audit_id, AuditActivity.is_deleted.is_(False)))
        if not exists:
            raise ValidationException("Selected activity does not belong to this audit.")

    def _apply_auditee_selection(self, db: Session, data: dict, *, require_linked_user: bool) -> None:
        assignment_directory_service.apply_auditee_selection(
            db,
            data,
            auditee_field="auditee_id",
            user_field="auditee_user_id",
            require_linked_user=require_linked_user,
            allow_direct_user_fallback=True,
            label="Observation auditee",
        )

    def create(self, db: Session, audit_id: int, payload: ObservationCreate, current_user: CurrentUser) -> Observation:
        assert_can_see_audit(db, audit_id, current_user)
        self._validate_activity(db, audit_id, payload.activity_id)
        data = payload.model_dump()
        self._apply_auditee_selection(db, data, require_linked_user=False)
        data["audit_id"] = audit_id
        data["status"] = ObservationStatus.DRAFT.value
        data["created_by"] = current_user.full_name
        data["updated_by"] = current_user.full_name
        observation = self.repo.create(db, data)
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="observations",
            entity_type="observation",
            entity_id=str(observation.id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(observation),
        )
        return observation

    def update(self, db: Session, observation_id: int, payload: ObservationUpdate, current_user: CurrentUser) -> Observation:
        observation = self.get(db, observation_id, current_user)
        if observation.status != ObservationStatus.DRAFT.value:
            raise ValidationException("Only draft observations can be edited.")
        data = payload.model_dump(exclude_none=True)
        self._validate_activity(db, observation.audit_id, data.get("activity_id", observation.activity_id))
        merged = {**model_to_dict(observation), **data}
        self._apply_auditee_selection(db, merged, require_linked_user=False)
        if "auditee_id" in data or "auditee_user_id" in data:
            data["auditee_id"] = merged.get("auditee_id")
            data["auditee_user_id"] = merged.get("auditee_user_id")
        before = model_to_dict(observation)
        data["updated_by"] = current_user.full_name
        observation = self.repo.update(db, observation, data)
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="observations",
            entity_type="observation",
            entity_id=str(observation.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=model_to_dict(observation),
        )
        return observation

    def issue(self, db: Session, observation_id: int, payload: ObservationIssueRequest, current_user: CurrentUser) -> Observation:
        observation = self.get(db, observation_id, current_user)
        if observation.status != ObservationStatus.DRAFT.value:
            raise ValidationException("Only draft observations can be issued.")
        data = {
            "auditee_id": payload.auditee_id or observation.auditee_id,
            "auditee_user_id": payload.auditee_user_id or observation.auditee_user_id,
        }
        self._apply_auditee_selection(db, data, require_linked_user=True)
        auditee_user_id = data.get("auditee_user_id")
        if not auditee_user_id:
            raise ValidationException("An auditee user is required before issuing an observation.")
        before = model_to_dict(observation)
        observation.auditee_id = data.get("auditee_id")
        observation.auditee_user_id = auditee_user_id
        observation.status = ObservationStatus.ISSUED.value
        observation.issued_at = datetime.now(UTC)
        observation.updated_by = current_user.full_name
        db.flush()
        activity_log_service.notify(db, user_id=auditee_user_id, title="Observation issued", message=f"Observation {observation.observation_number} requires your response.")
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="observations",
            entity_type="observation",
            entity_id=str(observation.id),
            action_type=ActivityAction.ISSUE.value,
            old_values=before,
            new_values=model_to_dict(observation),
        )
        return observation

    def respond(self, db: Session, observation_id: int, payload: ObservationResponseRequest, current_user: CurrentUser) -> Observation:
        observation = self.get(db, observation_id, current_user)
        if observation.status != ObservationStatus.ISSUED.value:
            raise ValidationException("Only issued observations can receive auditee responses.")
        if RoleCode.SUPER_ADMIN.value not in current_user.role_codes and observation.auditee_user_id != current_user.id:
            raise ForbiddenException("Only the assigned auditee can respond to this observation.")
        before = model_to_dict(observation)
        observation.auditee_remark = payload.auditee_remark
        observation.status = ObservationStatus.RESPONDED.value
        observation.responded_at = datetime.now(UTC)
        observation.updated_by = current_user.full_name
        db.flush()
        audit = db.get(Audit, observation.audit_id)
        if audit and audit.audit_owner_id:
            activity_log_service.notify(db, user_id=audit.audit_owner_id, title="Observation response submitted", message=f"Observation {observation.observation_number} has an auditee response.")
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role="auditee",
            module="observations",
            entity_type="observation",
            entity_id=str(observation.id),
            action_type=ActivityAction.RESPOND.value,
            old_values=before,
            new_values=model_to_dict(observation),
        )
        return observation

    def accept(self, db: Session, observation_id: int, payload: ObservationDispositionRequest, current_user: CurrentUser) -> Observation:
        observation = self.get(db, observation_id, current_user)
        if observation.status not in {ObservationStatus.RESPONDED.value, ObservationStatus.ISSUED.value}:
            raise ValidationException("Only issued or responded observations can be accepted.")
        before = model_to_dict(observation)
        observation.status = ObservationStatus.ACCEPTED.value
        observation.updated_by = current_user.full_name
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="observations",
            entity_type="observation",
            entity_id=str(observation.id),
            action_type=ActivityAction.REVIEW.value,
            old_values=before,
            new_values={**model_to_dict(observation), "remarks": payload.remarks},
        )
        return observation

    def drop(self, db: Session, observation_id: int, payload: ObservationDispositionRequest, current_user: CurrentUser) -> Observation:
        observation = self.get(db, observation_id, current_user)
        if observation.status in {ObservationStatus.CONVERTED.value, ObservationStatus.DROPPED.value}:
            raise ValidationException("Converted or dropped observations cannot be changed.")
        before = model_to_dict(observation)
        observation.status = ObservationStatus.DROPPED.value
        observation.updated_by = current_user.full_name
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="observations",
            entity_type="observation",
            entity_id=str(observation.id),
            action_type=ActivityAction.STATUS_CHANGE.value,
            old_values=before,
            new_values={**model_to_dict(observation), "remarks": payload.remarks},
        )
        return observation

    def convert_to_action_plan(self, db: Session, observation_id: int, payload: ObservationConvertRequest, current_user: CurrentUser) -> ActionPlan:
        observation = self.get(db, observation_id, current_user)
        if observation.status != ObservationStatus.ACCEPTED.value:
            raise ValidationException("Only accepted observations can be converted to action plans.")
        existing_action = db.scalar(select(ActionPlan).where(ActionPlan.observation_id == observation.id, ActionPlan.is_deleted.is_(False)))
        if existing_action:
            return existing_action
        audit = db.get(Audit, observation.audit_id)
        if not audit:
            raise NotFoundException("Audit not found.")
        implementation_owner_id = payload.implementation_owner_user_id or observation.auditee_user_id
        assigned_auditor_id = payload.assigned_auditor_user_id or audit.audit_owner_id or current_user.id
        if not implementation_owner_id:
            raise ValidationException("Implementation owner is required to convert an observation to an action plan.")
        before = model_to_dict(observation)
        action_plan = ActionPlan(
            audit_id=audit.id,
            observation_id=observation.id,
            location_id=audit.location_id,
            root_cause_id=observation.root_cause_id,
            observation_heading=observation.heading,
            observation_grading_id=observation.observation_grading_id,
            detailed_observation=observation.observation_text,
            risk_type_id=observation.risk_type_id,
            agreed_timeline=payload.agreed_timeline,
            auditor_status=ActionPlanStatus.PENDING.value,
            auditee_status=ActionPlanStatus.PENDING.value,
            responsibility_department=payload.responsibility_department,
            management_response=observation.auditee_remark,
            agreed_action_plan=payload.agreed_action_plan or observation.recommendation,
            implementation_owner_user_id=implementation_owner_id,
            assigned_auditor_user_id=assigned_auditor_id,
            revision_count=0,
            created_by=current_user.full_name,
            updated_by=current_user.full_name,
        )
        db.add(action_plan)
        observation.status = ObservationStatus.CONVERTED.value
        observation.updated_by = current_user.full_name
        db.flush()
        db.refresh(action_plan)
        action_plan_service._add_revision(
            db,
            action_plan=action_plan,
            revision_number=0,
            remarks=action_plan.management_response,
            revised_date=None,
            updated_by_user_id=current_user.id,
            attachment_id=None,
        )
        activity_log_service.notify(db, user_id=implementation_owner_id, title="Action plan assigned", message=f"Action plan {action_plan.action_plan_id} was created from observation {observation.observation_number}.")
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="observations",
            entity_type="observation",
            entity_id=str(observation.id),
            action_type=ActivityAction.CONVERT.value,
            old_values=before,
            new_values={"observation": model_to_dict(observation), "action_plan_id": action_plan.id},
        )
        return action_plan_service.get(db, action_plan.id)


observation_service = ObservationService()
