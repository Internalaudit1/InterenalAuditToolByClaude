from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser
from app.core.enums import (
    ActivityAction,
    AllocationStatus,
    AuditEventType,
    AuditMembershipRole,
    AuditPlanApprovalStatus,
    AuditStatus,
)
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.audit import Audit, AuditAllocation, AuditPlan
from app.models.reference_counter import _next_business_reference
from app.repositories.base import BaseRepository
from app.schemas.audit_allocation import AuditAllocationCreate, AuditAllocationUpdate
from app.schemas.common import ListQuery, PaginatedResponse, PaginationMeta
from app.services.activity_log import activity_log_service
from app.services.assignment_directory import assignment_directory_service
from app.services.audit import audit_service
from app.services.audit_event import audit_event_service
from app.utils.serialization import model_to_dict


class AuditAllocationService:
    repo = BaseRepository(AuditAllocation)

    def _get(self, db: Session, allocation_id: int) -> AuditAllocation:
        allocation = self.repo.get(db, allocation_id)
        if not allocation:
            raise NotFoundException("Audit allocation not found.")
        return allocation

    def _generate_code(self, db: Session, ref_year: int) -> str:
        return _next_business_reference(
            db.connection(),
            entity_name="audit_allocation",
            prefix="ALC",
            ref_year=ref_year,
        )

    def _validate_people(self, db: Session, data: dict, existing: AuditAllocation | None = None) -> None:
        lead_id = data.get("lead_auditor_user_id", existing.lead_auditor_user_id if existing else None)
        if not lead_id:
            raise ValidationException("A Lead Auditor is required for allocation.")
        assignment_directory_service.validate_internal_user(db, lead_id, "Lead Auditor")
        for field, label in (
            ("junior_auditor_1_id", "Junior Auditor 1"),
            ("junior_auditor_2_id", "Junior Auditor 2"),
            ("mentor_user_id", "Mentor"),
        ):
            user_id = data.get(field)
            if user_id:
                assignment_directory_service.validate_internal_user(db, user_id, label)
        if data.get("auditee_spoc_auditee_id") or data.get("auditee_spoc_user_id"):
            assignment_directory_service.apply_auditee_selection(
                db,
                data,
                auditee_field="auditee_spoc_auditee_id",
                user_field="auditee_spoc_user_id",
                require_linked_user=False,
                allow_direct_user_fallback=True,
                label="Auditee SPOC",
            )

    def list(self, db: Session, query: ListQuery, current_user: CurrentUser) -> PaginatedResponse[AuditAllocation]:
        stmt = select(AuditAllocation).where(AuditAllocation.is_deleted.is_(False))
        if query.search:
            stmt = stmt.where(
                or_(
                    AuditAllocation.allocation_code.ilike(f"%{query.search}%"),
                    AuditAllocation.status.ilike(f"%{query.search}%"),
                )
            )
        if query.filters and query.filters.get("status"):
            stmt = stmt.where(AuditAllocation.status == query.filters["status"])
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if query.sort_by and hasattr(AuditAllocation, query.sort_by):
            column = getattr(AuditAllocation, query.sort_by)
            stmt = stmt.order_by(desc(column) if query.sort_order == "desc" else asc(column))
        else:
            stmt = stmt.order_by(desc(AuditAllocation.updated_at))
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        return PaginatedResponse(
            items=list(db.scalars(stmt).all()),
            meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total),
        )

    def available_plans(self, db: Session, current_user: CurrentUser) -> list[AuditPlan]:
        allocated_plan_ids = select(AuditAllocation.audit_plan_id).where(AuditAllocation.is_deleted.is_(False))
        stmt = (
            select(AuditPlan)
            .where(
                AuditPlan.is_deleted.is_(False),
                AuditPlan.approval_status == AuditPlanApprovalStatus.APPROVED.value,
                AuditPlan.id.not_in(allocated_plan_ids),
            )
            .order_by(desc(AuditPlan.updated_at))
        )
        return list(db.scalars(stmt).all())

    def get(self, db: Session, allocation_id: int, current_user: CurrentUser) -> AuditAllocation:
        return self._get(db, allocation_id)

    def create(self, db: Session, payload: AuditAllocationCreate, actor_name: str, actor_id: int | None) -> AuditAllocation:
        data = payload.model_dump(exclude_none=True)
        audit_plan = audit_service.get_audit_plan(db, data["audit_plan_id"])
        if audit_plan.approval_status != AuditPlanApprovalStatus.APPROVED.value:
            raise ValidationException("Only approved audit plans can be allocated.")
        existing = db.scalar(
            select(AuditAllocation).where(
                AuditAllocation.audit_plan_id == audit_plan.id,
                AuditAllocation.is_deleted.is_(False),
            )
        )
        if existing:
            raise ConflictException("This audit plan is already allocated.")
        self._validate_people(db, data)
        ref_year = int(str(audit_plan.fiscal_year).split("-")[0]) if audit_plan.fiscal_year else datetime.now(UTC).year
        data["allocation_code"] = self._generate_code(db, ref_year)
        data["status"] = AllocationStatus.DRAFT.value
        data["created_by"] = actor_name
        data["updated_by"] = actor_name
        data["created_by_user_id"] = actor_id
        data["updated_by_user_id"] = actor_id
        allocation = self.repo.create(db, data)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type="audit_allocation",
            entity_id=str(allocation.id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(allocation),
        )
        return allocation

    def update(self, db: Session, allocation_id: int, payload: AuditAllocationUpdate, actor_name: str, actor_id: int | None) -> AuditAllocation:
        allocation = self._get(db, allocation_id)
        if allocation.status != AllocationStatus.DRAFT.value:
            raise ValidationException("Only draft allocations can be edited.")
        before = model_to_dict(allocation)
        data = payload.model_dump(exclude_unset=True)
        if {"lead_auditor_user_id", "junior_auditor_1_id", "junior_auditor_2_id", "mentor_user_id", "auditee_spoc_auditee_id", "auditee_spoc_user_id"} & set(data):
            self._validate_people(db, data, allocation)
        data["updated_by"] = actor_name
        data["updated_by_user_id"] = actor_id
        allocation = self.repo.update(db, allocation, data)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type="audit_allocation",
            entity_id=str(allocation.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=model_to_dict(allocation),
        )
        return allocation

    def approve(self, db: Session, allocation_id: int, actor_name: str, actor_id: int | None) -> AuditAllocation:
        allocation = self._get(db, allocation_id)
        if allocation.status != AllocationStatus.DRAFT.value:
            raise ValidationException("Only draft allocations can be approved.")
        before = model_to_dict(allocation)
        allocation.status = AllocationStatus.ALLOCATED.value
        allocation.approved_by_user_id = actor_id
        allocation.approved_at = datetime.now(UTC)
        allocation.updated_by = actor_name
        allocation.updated_by_user_id = actor_id
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type="audit_allocation",
            entity_id=str(allocation.id),
            action_type=ActivityAction.APPROVE.value,
            old_values=before,
            new_values=model_to_dict(allocation),
        )
        return allocation

    def cancel(self, db: Session, allocation_id: int, actor_name: str, actor_id: int | None) -> None:
        allocation = self._get(db, allocation_id)
        if allocation.status == AllocationStatus.INITIATED.value:
            raise ValidationException("An allocation that already created an audit cannot be cancelled.")
        allocation.is_deleted = True
        allocation.deleted_at = datetime.now(UTC)
        allocation.status = AllocationStatus.CANCELLED.value
        allocation.updated_by = actor_name
        allocation.updated_by_user_id = actor_id
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type="audit_allocation",
            entity_id=str(allocation.id),
            action_type=ActivityAction.DELETE.value,
        )

    def initiate_audit(self, db: Session, allocation_id: int, actor_name: str, actor_id: int | None) -> Audit:
        allocation = self._get(db, allocation_id)
        if allocation.status != AllocationStatus.ALLOCATED.value:
            raise ValidationException("Only approved (Allocated) allocations can initiate an audit.")
        if allocation.audit_id:
            existing = db.get(Audit, allocation.audit_id)
            if existing and not existing.is_deleted:
                return existing
        if not (allocation.start_date and allocation.end_date and allocation.period_value):
            raise ValidationException("Set Period, Start Date and Completion Date on the allocation before initiating the audit.")
        audit_plan = audit_service.get_audit_plan(db, allocation.audit_plan_id)
        assignment_directory_service.validate_internal_user(db, allocation.lead_auditor_user_id, "Lead Auditor")
        junior_ids = [uid for uid in (allocation.junior_auditor_1_id, allocation.junior_auditor_2_id) if uid]
        assignment_entry = {
            "action": "initiated_from_allocation",
            "by": actor_name,
            "at": datetime.now(UTC).isoformat(),
            "allocation_id": allocation.id,
            "lead_auditor_user_id": allocation.lead_auditor_user_id,
            "reviewer_user_id": allocation.mentor_user_id,
            "auditee_spoc_user_id": allocation.auditee_spoc_user_id,
            "auditee_spoc_auditee_id": allocation.auditee_spoc_auditee_id,
            "junior_auditor_user_ids": junior_ids,
        }
        audit = Audit(
            audit_plan_id=audit_plan.id,
            audit_name=audit_plan.audit_name,
            company_id=audit_plan.company_id,
            location_id=audit_plan.location_id,
            quarter=allocation.period_value,
            period_type=allocation.period_type,
            period_value=allocation.period_value,
            fiscal_year=audit_plan.fiscal_year,
            start_date=allocation.start_date,
            end_date=allocation.end_date,
            status=AuditStatus.TO_BE_INITIATED.value,
            planned_flag=True,
            criticality=audit_plan.criticality or "Medium",
            audit_owner_id=allocation.lead_auditor_user_id,
            reviewer_user_id=allocation.mentor_user_id,
            auditee_spoc_user_id=allocation.auditee_spoc_user_id,
            auditee_spoc_auditee_id=allocation.auditee_spoc_auditee_id,
            remarks=allocation.remarks,
            history_timeline=[{"status": AuditStatus.TO_BE_INITIATED.value, "note": "Initiated from audit allocation", "by": actor_name}],
            assignment_history=[assignment_entry],
            created_by=actor_name,
            updated_by=actor_name,
            created_by_user_id=actor_id,
            updated_by_user_id=actor_id,
        )
        db.add(audit)
        db.flush()
        db.refresh(audit)
        audit_service._add_audit_membership(db, audit_id=audit.id, user_id=allocation.lead_auditor_user_id, role_on_audit=AuditMembershipRole.LEAD_AUDITOR.value, actor_name=actor_name, actor_id=actor_id)
        audit_service._add_audit_membership(db, audit_id=audit.id, user_id=allocation.mentor_user_id, role_on_audit=AuditMembershipRole.REVIEWER.value, actor_name=actor_name, actor_id=actor_id)
        audit_service._add_audit_membership(db, audit_id=audit.id, user_id=allocation.auditee_spoc_user_id, role_on_audit=AuditMembershipRole.AUDITEE_SPOC.value, actor_name=actor_name, actor_id=actor_id)
        for junior_id in junior_ids:
            audit_service._add_audit_membership(db, audit_id=audit.id, user_id=junior_id, role_on_audit=AuditMembershipRole.JUNIOR_AUDITOR.value, actor_name=actor_name, actor_id=actor_id)
        allocation.audit_id = audit.id
        allocation.status = AllocationStatus.INITIATED.value
        allocation.updated_by = actor_name
        allocation.updated_by_user_id = actor_id
        db.flush()
        audit_event_service.record(
            db,
            audit=audit,
            event_type=AuditEventType.AUDIT_INITIATED,
            event_title="Audit initiated",
            actor_name=actor_name,
            actor_id=actor_id,
            description="Audit created from audit allocation.",
            to_status=AuditStatus.TO_BE_INITIATED.value,
            payload={"audit_allocation_id": allocation.id, "assignment_history": assignment_entry},
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="audits",
            entity_type="audit",
            entity_id=str(audit.id),
            action_type=ActivityAction.CREATE.value,
            new_values={"audit": model_to_dict(audit), "initiated_from_allocation_id": allocation.id},
        )
        activity_log_service.notify(
            db,
            user_id=allocation.lead_auditor_user_id,
            title="Audit initiated",
            message=f"{audit.audit_number} is ready for engagement planning.",
            actor_user_id=actor_id,
            actor_name=actor_name,
            payload={"audit_id": audit.id, "audit_number": audit.audit_number},
        )
        return audit


audit_allocation_service = AuditAllocationService()
