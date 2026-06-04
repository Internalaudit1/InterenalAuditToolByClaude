from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser
from app.core.enums import (
    ActivityAction,
    AuditMembershipRole,
    AuditEventType,
    EngagementDocumentType,
    EngagementPlanStatus,
    EngagementResourceRole,
    NotificationOutboxStatus,
    RoleCode,
)
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.models.audit import Audit, AuditMembership
from app.models.engagement import EngagementDocument, EngagementKickoffChecklist, EngagementPlan, EngagementResource
from app.models.support import Attachment
from app.repositories.base import BaseRepository
from app.schemas.common import ListQuery, PaginationMeta, PaginatedResponse
from app.schemas.engagement import (
    EngagementDecisionRequest,
    EngagementPlanCreate,
    EngagementPlanPrefillResponse,
    EngagementPlanUpdate,
    EngagementResourceCreate,
    EngagementResourceUpdate,
    KickoffChecklistPatchRequest,
)
from app.services.activity_log import activity_log_service
from app.services.assignment_directory import assignment_directory_service
from app.services.audit_event import audit_event_service
from app.services.audit_scope import membership_audit_ids_stmt
from app.services.authorization import ensure_same_company_location, has_global_scope
from app.utils.serialization import model_to_dict


DEFAULT_KICKOFF_ITEMS = [
    ("Engagement objective agreed with stakeholders", True),
    ("Scope and exclusions documented", True),
    ("Kickoff meeting scheduled", True),
    ("Initial data request shared", True),
    ("Resource budget aligned to execution plan", False),
]


class EngagementService:
    plan_repo = BaseRepository(EngagementPlan)
    checklist_repo = BaseRepository(EngagementKickoffChecklist)
    resource_repo = BaseRepository(EngagementResource)
    document_repo = BaseRepository(EngagementDocument)

    def _stamp_create(self, data: dict, current_user: CurrentUser) -> None:
        data["created_by"] = current_user.full_name
        data["updated_by"] = current_user.full_name
        data["created_by_user_id"] = current_user.id
        data["updated_by_user_id"] = current_user.id

    def _stamp_update(self, data: dict, current_user: CurrentUser) -> None:
        data["updated_by"] = current_user.full_name
        data["updated_by_user_id"] = current_user.id

    def _visible_stmt(self, current_user: CurrentUser):
        stmt = select(EngagementPlan).where(EngagementPlan.is_deleted.is_(False))
        if has_global_scope(current_user):
            return stmt
        resource_subquery = (
            select(EngagementResource.engagement_plan_id)
            .where(EngagementResource.user_id == current_user.id, EngagementResource.is_deleted.is_(False))
        )
        return stmt.where(
            or_(
                EngagementPlan.lead_auditor_id == current_user.id,
                EngagementPlan.reviewer_id == current_user.id,
                EngagementPlan.auditee_spoc_id == current_user.id,
                EngagementPlan.id.in_(resource_subquery),
                EngagementPlan.audit_id.in_(membership_audit_ids_stmt(current_user)),
            )
        )

    def _get_visible_plan(self, db: Session, engagement_plan_id: int, current_user: CurrentUser) -> EngagementPlan:
        plan = db.scalar(self._visible_stmt(current_user).where(EngagementPlan.id == engagement_plan_id).limit(1))
        if not plan:
            raise NotFoundException("Engagement plan not found.")
        return plan

    def _get_audit(self, db: Session, audit_id: int) -> Audit:
        audit = db.scalar(select(Audit).where(Audit.id == audit_id, Audit.is_deleted.is_(False)))
        if not audit:
            raise NotFoundException("Audit not found.")
        return audit

    def _assert_can_start_for_audit(self, db: Session, audit: Audit, current_user: CurrentUser) -> None:
        if has_global_scope(current_user):
            return
        if audit.audit_owner_id == current_user.id:
            return
        is_lead_member = db.scalar(
            select(AuditMembership.id).where(
                AuditMembership.audit_id == audit.id,
                AuditMembership.user_id == current_user.id,
                AuditMembership.role_on_audit == AuditMembershipRole.LEAD_AUDITOR.value,
                AuditMembership.is_deleted.is_(False),
            )
        )
        if is_lead_member:
            return
        raise ForbiddenException("Only the assigned Lead Auditor can start engagement planning for this audit.")

    def _default_objective(self, audit: Audit) -> str:
        period_bits = [bit for bit in [audit.period_value or audit.quarter, audit.fiscal_year] if bit]
        period_text = " ".join(period_bits).strip()
        suffix = f" for {period_text}" if period_text else ""
        return f"Plan and execute the internal audit of {audit.audit_name}{suffix}."

    def _default_scope(self, audit: Audit) -> str:
        return (
            f"Review the assigned risks, controls, and fieldwork requirements for {audit.audit_name} "
            "at the scoped company and location."
        )

    def _validate_people(self, db: Session, data: dict) -> None:
        if data.get("lead_auditor_id"):
            assignment_directory_service.validate_internal_user(db, data["lead_auditor_id"], "Lead Auditor")
        if data.get("reviewer_id"):
            assignment_directory_service.validate_internal_user(db, data["reviewer_id"], "Reviewer")
        assignment_directory_service.apply_auditee_selection(
            db,
            data,
            auditee_field="auditee_spoc_auditee_id",
            user_field="auditee_spoc_id",
            require_linked_user=False,
            allow_direct_user_fallback=True,
            label="Auditee SPOC",
        )

    def prefill_for_audit(self, db: Session, audit_id: int, current_user: CurrentUser) -> EngagementPlanPrefillResponse:
        audit = self._get_audit(db, audit_id)
        self._assert_can_start_for_audit(db, audit, current_user)
        existing_plan = db.scalar(
            select(EngagementPlan).where(
                EngagementPlan.audit_id == audit.id,
                EngagementPlan.is_deleted.is_(False),
            )
        )
        lead_auditor_id = audit.audit_owner_id or current_user.id
        return EngagementPlanPrefillResponse(
            audit_id=audit.id,
            audit_number=audit.audit_number,
            audit_name=audit.audit_name,
            company_id=audit.company_id,
            location_id=audit.location_id,
            title=f"{audit.audit_name} Engagement Plan",
            objective=self._default_objective(audit),
            scope=self._default_scope(audit),
            scope_exclusions=None,
            audit_period_from=audit.start_date,
            audit_period_to=audit.end_date,
            kickoff_date=None,
            planned_start_date=audit.start_date,
            planned_end_date=audit.end_date,
            lead_auditor_id=lead_auditor_id,
            reviewer_id=audit.reviewer_user_id,
            auditee_spoc_auditee_id=audit.auditee_spoc_auditee_id,
            auditee_spoc_id=audit.auditee_spoc_user_id,
            lead_auditor_name=audit.audit_owner_name,
            reviewer_name=audit.reviewer_name,
            auditee_spoc_name=audit.auditee_spoc_name,
            planned_hours=None,
            approved_hours=None,
            can_create=existing_plan is None,
            existing_engagement_plan_id=existing_plan.id if existing_plan else None,
        )

    def _assert_can_manage_draft(self, plan: EngagementPlan, current_user: CurrentUser) -> None:
        if has_global_scope(current_user):
            return
        if plan.lead_auditor_id != current_user.id:
            raise ForbiddenException("Only the assigned Lead Auditor can edit this engagement plan.")
        if plan.status not in {EngagementPlanStatus.DRAFT.value, EngagementPlanStatus.REJECTED.value}:
            raise ForbiddenException("Only draft or rejected engagement plans can be edited by the Lead Auditor.")

    def _assert_can_approve(self, plan: EngagementPlan, current_user: CurrentUser) -> None:
        if RoleCode.SUPER_ADMIN.value in current_user.role_codes or RoleCode.HEAD_AUDITOR.value in current_user.role_codes:
            ensure_same_company_location(current_user=current_user, company_id=plan.company_id, location_id=plan.location_id)
            return
        raise ForbiddenException("Only Super Admin or Head Auditor can approve or reject engagement plans.")

    def _ensure_default_checklist(self, db: Session, plan: EngagementPlan, current_user: CurrentUser) -> None:
        if any(not item.is_deleted for item in plan.kickoff_checklist_items):
            return
        for label, mandatory in DEFAULT_KICKOFF_ITEMS:
            self.checklist_repo.create(
                db,
                {
                    "engagement_plan_id": plan.id,
                    "check_item": label,
                    "is_mandatory": mandatory,
                    "is_completed": False,
                    "created_by": current_user.full_name,
                    "updated_by": current_user.full_name,
                    "created_by_user_id": current_user.id,
                    "updated_by_user_id": current_user.id,
                },
            )

    def _upsert_resource(
        self,
        db: Session,
        *,
        plan: EngagementPlan,
        user_id: int | None,
        role_in_engagement: EngagementResourceRole,
        current_user: CurrentUser,
    ) -> None:
        if not user_id:
            return
        existing = db.scalar(
            select(EngagementResource).where(
                EngagementResource.engagement_plan_id == plan.id,
                EngagementResource.user_id == user_id,
                EngagementResource.role_in_engagement == role_in_engagement.value,
            )
        )
        if existing:
            existing.is_deleted = False
            existing.deleted_at = None
            existing.updated_by = current_user.full_name
            existing.updated_by_user_id = current_user.id
            db.flush()
            return
        self.resource_repo.create(
            db,
            {
                "engagement_plan_id": plan.id,
                "user_id": user_id,
                "role_in_engagement": role_in_engagement.value,
                "created_by": current_user.full_name,
                "updated_by": current_user.full_name,
                "created_by_user_id": current_user.id,
                "updated_by_user_id": current_user.id,
            },
        )

    def _sync_key_resources(self, db: Session, plan: EngagementPlan, current_user: CurrentUser) -> None:
        self._upsert_resource(db, plan=plan, user_id=plan.lead_auditor_id, role_in_engagement=EngagementResourceRole.LEAD_AUDITOR, current_user=current_user)
        self._upsert_resource(db, plan=plan, user_id=plan.reviewer_id, role_in_engagement=EngagementResourceRole.REVIEWER, current_user=current_user)
        self._upsert_resource(db, plan=plan, user_id=plan.auditee_spoc_id, role_in_engagement=EngagementResourceRole.AUDITEE_SPOC, current_user=current_user)

    def list(self, db: Session, query: ListQuery, current_user: CurrentUser) -> PaginatedResponse[EngagementPlan]:
        stmt = self._visible_stmt(current_user)
        if query.filters:
            for field, value in query.filters.items():
                if value in (None, "", []):
                    continue
                if hasattr(EngagementPlan, field):
                    stmt = stmt.where(getattr(EngagementPlan, field) == value)
        if query.search:
            stmt = stmt.where(
                or_(
                    EngagementPlan.engagement_code.ilike(f"%{query.search}%"),
                    EngagementPlan.title.ilike(f"%{query.search}%"),
                    EngagementPlan.status.ilike(f"%{query.search}%"),
                )
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if query.sort_by and hasattr(EngagementPlan, query.sort_by):
            sort_column = getattr(EngagementPlan, query.sort_by)
            stmt = stmt.order_by(desc(sort_column) if query.sort_order == "desc" else asc(sort_column))
        else:
            stmt = stmt.order_by(desc(EngagementPlan.updated_at))
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        return PaginatedResponse(
            items=list(db.scalars(stmt).all()),
            meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total),
        )

    def get(self, db: Session, engagement_plan_id: int, current_user: CurrentUser) -> EngagementPlan:
        return self._get_visible_plan(db, engagement_plan_id, current_user)

    def create(self, db: Session, payload: EngagementPlanCreate, current_user: CurrentUser) -> EngagementPlan:
        audit = self._get_audit(db, payload.audit_id)
        self._assert_can_start_for_audit(db, audit, current_user)
        existing = db.scalar(
            select(EngagementPlan.id).where(
                EngagementPlan.audit_id == audit.id,
                EngagementPlan.is_deleted.is_(False),
            )
        )
        if existing:
            raise ValidationException("An active engagement plan already exists for this audit.")
        data = payload.model_dump()
        data["company_id"] = audit.company_id
        data["location_id"] = audit.location_id
        data["lead_auditor_id"] = data.get("lead_auditor_id") or audit.audit_owner_id or current_user.id
        self._validate_people(db, data)
        if not has_global_scope(current_user) and data["lead_auditor_id"] != current_user.id:
            raise ForbiddenException("Lead Auditors can only create engagement plans for themselves.")
        data["status"] = EngagementPlanStatus.DRAFT.value
        self._stamp_create(data, current_user)
        plan = self.plan_repo.create(db, data)
        self._ensure_default_checklist(db, plan, current_user)
        self._sync_key_resources(db, plan, current_user)
        audit_event_service.record(
            db,
            audit=audit,
            event_type=AuditEventType.ENGAGEMENT_CREATED,
            event_title="Engagement plan created",
            actor_name=current_user.full_name,
            actor_id=current_user.id,
            description=plan.title,
            payload={"engagement_plan_id": plan.id, "engagement_code": plan.engagement_code},
        )
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="engagement_plans",
            entity_type="engagement_plan",
            entity_id=str(plan.id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(plan),
        )
        return self.get(db, plan.id, current_user)

    def update(self, db: Session, engagement_plan_id: int, payload: EngagementPlanUpdate, current_user: CurrentUser) -> EngagementPlan:
        plan = self._get_visible_plan(db, engagement_plan_id, current_user)
        self._assert_can_manage_draft(plan, current_user)
        before = model_to_dict(plan)
        data = payload.model_dump(exclude_none=True)
        self._validate_people(db, data)
        self._stamp_update(data, current_user)
        plan = self.plan_repo.update(db, plan, data)
        self._sync_key_resources(db, plan, current_user)
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="engagement_plans",
            entity_type="engagement_plan",
            entity_id=str(plan.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=model_to_dict(plan),
        )
        return self.get(db, plan.id, current_user)

    def _change_status(
        self,
        db: Session,
        engagement_plan_id: int,
        *,
        target_status: EngagementPlanStatus,
        current_user: CurrentUser,
        remarks: str | None = None,
    ) -> EngagementPlan:
        plan = self._get_visible_plan(db, engagement_plan_id, current_user)
        before = model_to_dict(plan)
        if target_status == EngagementPlanStatus.SUBMITTED:
            self._assert_can_manage_draft(plan, current_user)
            if plan.status not in {EngagementPlanStatus.DRAFT.value, EngagementPlanStatus.REJECTED.value}:
                raise ValidationException("Only draft or rejected engagement plans can be submitted.")
            if not plan.objective or not plan.scope:
                raise ValidationException("Objective and scope are required before submission.")
        elif target_status in {EngagementPlanStatus.APPROVED, EngagementPlanStatus.REJECTED}:
            self._assert_can_approve(plan, current_user)
            if plan.status != EngagementPlanStatus.SUBMITTED.value:
                raise ValidationException("Only submitted engagement plans can be approved or rejected.")
        else:
            raise ValidationException("Unsupported engagement status transition.")

        plan.status = target_status.value
        plan.updated_by = current_user.full_name
        plan.updated_by_user_id = current_user.id
        db.flush()

        event_type = {
            EngagementPlanStatus.SUBMITTED: AuditEventType.ENGAGEMENT_SUBMITTED,
            EngagementPlanStatus.APPROVED: AuditEventType.ENGAGEMENT_APPROVED,
            EngagementPlanStatus.REJECTED: AuditEventType.ENGAGEMENT_REJECTED,
        }[target_status]
        event_title = {
            EngagementPlanStatus.SUBMITTED: "Engagement plan submitted",
            EngagementPlanStatus.APPROVED: "Engagement plan approved",
            EngagementPlanStatus.REJECTED: "Engagement plan rejected",
        }[target_status]
        audit_event_service.record(
            db,
            audit=plan.audit,
            event_type=event_type,
            event_title=event_title,
            actor_name=current_user.full_name,
            actor_id=current_user.id,
            from_status=before.get("status"),
            to_status=plan.status,
            description=remarks,
            payload={"engagement_plan_id": plan.id, "engagement_code": plan.engagement_code},
        )
        if target_status == EngagementPlanStatus.SUBMITTED and plan.reviewer_id:
            activity_log_service.notify(
                db,
                user_id=plan.reviewer_id,
                title="Engagement plan submitted",
                message=f"{plan.engagement_code} is ready for review.",
                actor_user_id=current_user.id,
                actor_name=current_user.full_name,
                payload={"engagement_plan_id": plan.id, "status": plan.status},
            )
        if target_status in {EngagementPlanStatus.APPROVED, EngagementPlanStatus.REJECTED} and plan.lead_auditor_id:
            activity_log_service.notify(
                db,
                user_id=plan.lead_auditor_id,
                title=f"Engagement plan {plan.status.lower()}",
                message=f"{plan.engagement_code} moved to {plan.status}.",
                actor_user_id=current_user.id,
                actor_name=current_user.full_name,
                payload={"engagement_plan_id": plan.id, "status": plan.status},
            )
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="engagement_plans",
            entity_type="engagement_plan",
            entity_id=str(plan.id),
            action_type=ActivityAction.STATUS_CHANGE.value if target_status != EngagementPlanStatus.APPROVED else ActivityAction.APPROVE.value,
            old_values=before,
            new_values={**model_to_dict(plan), "remarks": remarks},
        )
        return self.get(db, plan.id, current_user)

    def submit(self, db: Session, engagement_plan_id: int, current_user: CurrentUser) -> EngagementPlan:
        return self._change_status(db, engagement_plan_id, target_status=EngagementPlanStatus.SUBMITTED, current_user=current_user)

    def approve(self, db: Session, engagement_plan_id: int, current_user: CurrentUser, payload: EngagementDecisionRequest | None = None) -> EngagementPlan:
        return self._change_status(
            db,
            engagement_plan_id,
            target_status=EngagementPlanStatus.APPROVED,
            current_user=current_user,
            remarks=payload.remarks if payload else None,
        )

    def reject(self, db: Session, engagement_plan_id: int, current_user: CurrentUser, payload: EngagementDecisionRequest | None = None) -> EngagementPlan:
        return self._change_status(
            db,
            engagement_plan_id,
            target_status=EngagementPlanStatus.REJECTED,
            current_user=current_user,
            remarks=payload.remarks if payload else None,
        )

    def list_checklist(self, db: Session, engagement_plan_id: int, current_user: CurrentUser) -> list[EngagementKickoffChecklist]:
        self._get_visible_plan(db, engagement_plan_id, current_user)
        return list(
            db.scalars(
                select(EngagementKickoffChecklist)
                .where(
                    EngagementKickoffChecklist.engagement_plan_id == engagement_plan_id,
                    EngagementKickoffChecklist.is_deleted.is_(False),
                )
                .order_by(asc(EngagementKickoffChecklist.id))
            ).all()
        )

    def patch_checklist(self, db: Session, engagement_plan_id: int, payload: KickoffChecklistPatchRequest, current_user: CurrentUser) -> list[EngagementKickoffChecklist]:
        plan = self._get_visible_plan(db, engagement_plan_id, current_user)
        if not has_global_scope(current_user) and current_user.id not in {plan.lead_auditor_id, plan.reviewer_id}:
            raise ForbiddenException("Only the Lead Auditor or reviewer can update the kickoff checklist.")
        existing = {
            item.id: item
            for item in db.scalars(
                select(EngagementKickoffChecklist).where(
                    EngagementKickoffChecklist.engagement_plan_id == engagement_plan_id,
                    EngagementKickoffChecklist.is_deleted.is_(False),
                )
            ).all()
        }
        for item in payload.items:
            if item.id:
                checklist_item = existing.get(item.id)
                if not checklist_item:
                    raise NotFoundException("Kickoff checklist item not found.")
                checklist_item.check_item = item.check_item
                checklist_item.is_mandatory = item.is_mandatory
                checklist_item.is_completed = item.is_completed
                checklist_item.remarks = item.remarks
                checklist_item.updated_by = current_user.full_name
                checklist_item.updated_by_user_id = current_user.id
                checklist_item.completed_by_user_id = current_user.id if item.is_completed else None
                checklist_item.completed_at = datetime.now(UTC) if item.is_completed else None
            else:
                self.checklist_repo.create(
                    db,
                    {
                        "engagement_plan_id": engagement_plan_id,
                        "check_item": item.check_item,
                        "is_mandatory": item.is_mandatory,
                        "is_completed": item.is_completed,
                        "remarks": item.remarks,
                        "completed_by_user_id": current_user.id if item.is_completed else None,
                        "completed_at": datetime.now(UTC) if item.is_completed else None,
                        "created_by": current_user.full_name,
                        "updated_by": current_user.full_name,
                        "created_by_user_id": current_user.id,
                        "updated_by_user_id": current_user.id,
                    },
                )
        db.flush()
        mandatory_open = db.scalar(
            select(func.count())
            .select_from(EngagementKickoffChecklist)
            .where(
                EngagementKickoffChecklist.engagement_plan_id == engagement_plan_id,
                EngagementKickoffChecklist.is_deleted.is_(False),
                EngagementKickoffChecklist.is_mandatory.is_(True),
                EngagementKickoffChecklist.is_completed.is_(False),
            )
        ) or 0
        if plan.status == EngagementPlanStatus.APPROVED.value and mandatory_open == 0:
            before_status = plan.status
            plan.status = EngagementPlanStatus.KICKED_OFF.value
            plan.updated_by = current_user.full_name
            plan.updated_by_user_id = current_user.id
            audit_event_service.record(
                db,
                audit=plan.audit,
                event_type=AuditEventType.ENGAGEMENT_KICKED_OFF,
                event_title="Engagement kicked off",
                actor_name=current_user.full_name,
                actor_id=current_user.id,
                from_status=before_status,
                to_status=plan.status,
                payload={"engagement_plan_id": plan.id},
            )
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="engagement_plans",
            entity_type="engagement_kickoff_checklist",
            entity_id=str(engagement_plan_id),
            action_type=ActivityAction.UPDATE.value,
            new_values={"items": [item.model_dump() for item in payload.items], "status": plan.status},
        )
        return self.list_checklist(db, engagement_plan_id, current_user)

    def list_resources(self, db: Session, engagement_plan_id: int, current_user: CurrentUser) -> list[EngagementResource]:
        self._get_visible_plan(db, engagement_plan_id, current_user)
        return list(
            db.scalars(
                select(EngagementResource)
                .where(EngagementResource.engagement_plan_id == engagement_plan_id, EngagementResource.is_deleted.is_(False))
                .order_by(asc(EngagementResource.id))
            ).all()
        )

    def add_resource(self, db: Session, engagement_plan_id: int, payload: EngagementResourceCreate, current_user: CurrentUser) -> EngagementResource:
        plan = self._get_visible_plan(db, engagement_plan_id, current_user)
        if not has_global_scope(current_user) and plan.lead_auditor_id != current_user.id:
            raise ForbiddenException("Only the Lead Auditor can add engagement resources.")
        assignment_directory_service.validate_internal_user(db, payload.user_id, "Engagement resource")
        data = payload.model_dump()
        data["role_in_engagement"] = payload.role_in_engagement.value
        data["engagement_plan_id"] = engagement_plan_id
        self._stamp_create(data, current_user)
        resource = self.resource_repo.create(db, data)
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="engagement_plans",
            entity_type="engagement_resource",
            entity_id=str(resource.id),
            action_type=ActivityAction.ASSIGN.value,
            new_values=model_to_dict(resource),
        )
        return resource

    def update_resource(self, db: Session, engagement_plan_id: int, resource_id: int, payload: EngagementResourceUpdate, current_user: CurrentUser) -> EngagementResource:
        plan = self._get_visible_plan(db, engagement_plan_id, current_user)
        if not has_global_scope(current_user) and plan.lead_auditor_id != current_user.id:
            raise ForbiddenException("Only the Lead Auditor can update engagement resources.")
        resource = db.scalar(
            select(EngagementResource).where(
                EngagementResource.id == resource_id,
                EngagementResource.engagement_plan_id == engagement_plan_id,
                EngagementResource.is_deleted.is_(False),
            )
        )
        if not resource:
            raise NotFoundException("Engagement resource not found.")
        assignment_directory_service.validate_internal_user(db, resource.user_id, "Engagement resource")
        before = model_to_dict(resource)
        data = payload.model_dump(exclude_none=True)
        if "role_in_engagement" in data:
            data["role_in_engagement"] = payload.role_in_engagement.value
        self._stamp_update(data, current_user)
        resource = self.resource_repo.update(db, resource, data)
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="engagement_plans",
            entity_type="engagement_resource",
            entity_id=str(resource.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=model_to_dict(resource),
        )
        return resource

    def list_documents(self, db: Session, engagement_plan_id: int, current_user: CurrentUser) -> list[EngagementDocument]:
        self._get_visible_plan(db, engagement_plan_id, current_user)
        return list(
            db.scalars(
                select(EngagementDocument)
                .where(EngagementDocument.engagement_plan_id == engagement_plan_id, EngagementDocument.is_deleted.is_(False))
                .order_by(desc(EngagementDocument.is_latest), desc(EngagementDocument.created_at))
            ).all()
        )

    def prepare_document_upload(self, db: Session, engagement_plan_id: int, current_user: CurrentUser) -> EngagementPlan:
        plan = self._get_visible_plan(db, engagement_plan_id, current_user)
        if not has_global_scope(current_user) and plan.lead_auditor_id != current_user.id:
            raise ForbiddenException("Only the Lead Auditor can upload engagement documents.")
        return plan

    def add_document(
        self,
        db: Session,
        *,
        engagement_plan_id: int,
        document_type: EngagementDocumentType,
        file_name: str,
        stored_name: str,
        content_type: str,
        file_size: int,
        storage_path: str,
        current_user: CurrentUser,
    ) -> EngagementDocument:
        plan = self._get_visible_plan(db, engagement_plan_id, current_user)
        if not has_global_scope(current_user) and plan.lead_auditor_id != current_user.id:
            raise ForbiddenException("Only the Lead Auditor can upload engagement documents.")
        existing_latest = db.scalars(
            select(EngagementDocument).where(
                EngagementDocument.engagement_plan_id == engagement_plan_id,
                EngagementDocument.document_type == document_type.value,
                EngagementDocument.is_deleted.is_(False),
                EngagementDocument.is_latest.is_(True),
            )
        ).all()
        for existing in existing_latest:
            existing.is_latest = False
            existing.updated_by = current_user.full_name
            existing.updated_by_user_id = current_user.id
        attachment = Attachment(
            owner_type="engagement_plan",
            owner_id=engagement_plan_id,
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
        document = self.document_repo.create(
            db,
            {
                "engagement_plan_id": engagement_plan_id,
                "document_type": document_type.value,
                "document_id": attachment.id,
                "is_latest": True,
                "created_by": current_user.full_name,
                "updated_by": current_user.full_name,
                "created_by_user_id": current_user.id,
                "updated_by_user_id": current_user.id,
            },
        )
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="engagement_plans",
            entity_type="engagement_document",
            entity_id=str(document.id),
            action_type=ActivityAction.UPLOAD.value,
            new_values=model_to_dict(document),
        )
        return document


engagement_service = EngagementService()
