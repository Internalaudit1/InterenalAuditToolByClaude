from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import asc, case, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import CurrentUser
from app.core.enums import ActivityAction, AuditEventType, AuditMembershipRole, AuditPlanApprovalStatus, AuditStatus
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.models.auth import User
from app.models.action_plan import ActionPlan
from app.models.audit import Audit, AuditActivity, AuditMembership, AuditPlan
from app.repositories.base import BaseRepository
from app.schemas.audit import AuditCreate, AuditMembershipCreate, AuditPlanCreate, AuditPlanInitiateRequest, AuditPlanUpdate, AuditUpdate
from app.schemas.common import BlockedDeleteItem, BulkDeleteResponse, ListQuery, PaginationMeta, PaginatedResponse
from app.services.activity_log import activity_log_service
from app.services.assignment_directory import assignment_directory_service
from app.services.audit_event import audit_event_service
from app.services.audit_scope import apply_audit_scope, assert_can_see_audit, has_global_audit_visibility
from app.services.authorization import apply_company_location_scope, assert_company_location_access, ensure_same_company_location
from app.utils.serialization import model_to_dict


class AuditService:
    audit_repo = BaseRepository(Audit)
    audit_plan_repo = BaseRepository(AuditPlan)
    membership_repo = BaseRepository(AuditMembership)
    period_values = {
        "Monthly": {"January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"},
        "Quarterly": {"Q1", "Q2", "Q3", "Q4"},
        "Half-Yearly": {"H1", "H2"},
        "Annual": {"Full Year"},
    }
    fiscal_years = {f"{year}-{year + 1}" for year in range(2025, 2043)}
    audit_plan_transitions: dict[str, set[str]] = {
        AuditPlanApprovalStatus.DRAFT.value: {AuditPlanApprovalStatus.UNDER_REVIEW.value, AuditPlanApprovalStatus.DEFERRED.value, AuditPlanApprovalStatus.CANCELLED.value},
        AuditPlanApprovalStatus.UNDER_REVIEW.value: {AuditPlanApprovalStatus.APPROVED.value, AuditPlanApprovalStatus.DEFERRED.value, AuditPlanApprovalStatus.CANCELLED.value},
        AuditPlanApprovalStatus.DEFERRED.value: {AuditPlanApprovalStatus.DRAFT.value, AuditPlanApprovalStatus.CANCELLED.value},
        AuditPlanApprovalStatus.APPROVED.value: set(),
        AuditPlanApprovalStatus.CANCELLED.value: set(),
    }

    def _reject_generated_references(self, data: dict, fields: set[str]) -> None:
        blocked = sorted(field for field in fields if field in data)
        if blocked:
            raise ValidationException(f"Generated reference fields are backend-controlled and cannot be supplied: {', '.join(blocked)}.")

    def _validate_date_range(self, start_date, end_date) -> None:
        if start_date and end_date and end_date < start_date:
            raise ValidationException("End Date must be on or after Start Date.")

    def _validate_fiscal_year(self, fiscal_year: str | None) -> None:
        if fiscal_year and fiscal_year not in self.fiscal_years:
            raise ValidationException("Fiscal Year must be selected from the configured list.")

    def _period_from_value(self, value: str | None) -> tuple[str, str] | None:
        normalized = (value or "").strip()
        upper_value = normalized.upper()
        lower_value = normalized.lower()
        for month in self.period_values["Monthly"]:
            if lower_value == month.lower():
                return "Monthly", month
        if upper_value in self.period_values["Quarterly"]:
            return "Quarterly", upper_value
        if upper_value in self.period_values["Half-Yearly"]:
            return "Half-Yearly", upper_value
        if lower_value in {"full year", "fullyear", "annual", "year"}:
            return "Annual", "Full Year"
        return None

    def _validate_period_pair(self, period_type: str | None, period_value: str | None) -> tuple[str, str]:
        if not period_type:
            raise ValidationException("Period Type is required.")
        if not period_value:
            raise ValidationException("Period Value is required.")
        if period_type not in self.period_values:
            raise ValidationException("Period Type must be Monthly, Quarterly, Half-Yearly, or Annual.")
        if period_value not in self.period_values[period_type]:
            raise ValidationException("Period Value must match the selected Period Type.")
        return period_type, period_value

    def _validate_audit_plan_auditors(self, db: Session, data: dict, existing: AuditPlan | None = None) -> None:
        assignments = {
            "Lead Auditor": data.get("audit_owner_id", existing.audit_owner_id if existing else None),
            "Junior Auditor 1": data.get("junior_auditor_1_id", existing.junior_auditor_1_id if existing else None),
            "Junior Auditor 2": data.get("junior_auditor_2_id", existing.junior_auditor_2_id if existing else None),
        }
        selected = {label: user_id for label, user_id in assignments.items() if user_id}
        if len(set(selected.values())) != len(selected):
            raise ValidationException("Lead Auditor, Junior Auditor 1, and Junior Auditor 2 must be different users when selected.")
        for label, user_id in selected.items():
            assignment_directory_service.validate_internal_user(db, user_id, label)

    def _validate_audit_people(self, db: Session, data: dict, existing: Audit | None = None) -> None:
        audit_owner_id = data.get("audit_owner_id", existing.audit_owner_id if existing else None)
        reviewer_user_id = data.get("reviewer_user_id", existing.reviewer_user_id if existing else None)
        if audit_owner_id:
            assignment_directory_service.validate_internal_user(db, audit_owner_id, "Lead Auditor")
        if reviewer_user_id:
            assignment_directory_service.validate_internal_user(db, reviewer_user_id, "Reviewer")
        assignment_directory_service.apply_auditee_selection(
            db,
            data,
            auditee_field="auditee_spoc_auditee_id",
            user_field="auditee_spoc_user_id",
            require_linked_user=False,
            allow_direct_user_fallback=True,
            label="Auditee SPOC",
        )

    def _apply_audit_plan_period(self, data: dict, existing: AuditPlan | None = None) -> None:
        period_type = data.get("period_type", existing.period_type if existing else None)
        period_value = data.get("period_value", existing.period_value if existing else None)
        period_type, period_value = self._validate_period_pair(period_type, period_value)
        data["period_type"] = period_type
        data["period_value"] = period_value
        data["quarter"] = period_value
        self._validate_fiscal_year(data.get("fiscal_year", existing.fiscal_year if existing else None))

    def _apply_audit_period_compatibility(self, data: dict, existing: Audit | None = None) -> None:
        self._validate_fiscal_year(data.get("fiscal_year", existing.fiscal_year if existing else None))
        has_period_input = data.get("period_type") is not None or data.get("period_value") is not None
        if has_period_input:
            inferred = self._period_from_value(existing.quarter if existing else data.get("quarter"))
            current_type = existing.period_type if existing and existing.period_type else inferred[0] if inferred else None
            current_value = existing.period_value if existing and existing.period_value else inferred[1] if inferred else None
            period_type = data.get("period_type") or current_type
            period_value = data.get("period_value") or current_value
            period_type, period_value = self._validate_period_pair(period_type, period_value)
            data["period_type"] = period_type
            data["period_value"] = period_value
            data["quarter"] = period_value
            return

        if "quarter" in data:
            inferred = self._period_from_value(data.get("quarter"))
            if inferred:
                data["period_type"], data["period_value"] = inferred

    def list_audits(self, db: Session, query: ListQuery, current_user: CurrentUser | None = None, scope: str | None = None) -> PaginatedResponse[Audit]:
        stmt = select(Audit).where(Audit.is_deleted.is_(False))
        if current_user and (scope in {None, "mine", "team"} or not has_global_audit_visibility(current_user)):
            stmt = apply_audit_scope(stmt, current_user)
        if query.filters:
            for field, value in query.filters.items():
                if value in (None, "", []):
                    continue
                if hasattr(Audit, field):
                    stmt = stmt.where(getattr(Audit, field) == value)
        if query.search:
            clauses = [
                getattr(Audit, field).ilike(f"%{query.search}%")
                for field in ["audit_number", "audit_name", "status", "quarter", "period_type", "period_value", "fiscal_year"]
            ]
            stmt = stmt.where(or_(*clauses))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if query.sort_by and hasattr(Audit, query.sort_by):
            sort_column = getattr(Audit, query.sort_by)
            stmt = stmt.order_by(desc(sort_column) if query.sort_order == "desc" else asc(sort_column))
        else:
            stmt = stmt.order_by(desc(Audit.updated_at))
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        items = list(db.scalars(stmt).all())
        return PaginatedResponse(items=items, meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def list_audit_plans(self, db: Session, query: ListQuery, current_user: CurrentUser | None = None) -> PaginatedResponse[AuditPlan]:
        stmt = select(AuditPlan).where(AuditPlan.is_deleted.is_(False))
        if current_user:
            stmt = apply_company_location_scope(stmt, current_user, company_column=AuditPlan.company_id, location_column=AuditPlan.location_id)
        if query.filters:
            for field, value in query.filters.items():
                if value in (None, "", []):
                    continue
                if hasattr(AuditPlan, field):
                    stmt = stmt.where(getattr(AuditPlan, field) == value)
        if query.search:
            clauses = [
                getattr(AuditPlan, field).ilike(f"%{query.search}%")
                for field in ["audit_number", "audit_name", "quarter", "period_type", "period_value", "fiscal_year"]
            ]
            stmt = stmt.where(or_(*clauses))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if query.sort_by and hasattr(AuditPlan, query.sort_by):
            sort_column = getattr(AuditPlan, query.sort_by)
            stmt = stmt.order_by(desc(sort_column) if query.sort_order == "desc" else asc(sort_column))
        else:
            stmt = stmt.order_by(desc(AuditPlan.updated_at))
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        items = list(db.scalars(stmt).all())
        return PaginatedResponse(items=items, meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def get_audit(self, db: Session, audit_id: int, current_user: CurrentUser | None = None) -> Audit:
        if current_user:
            assert_can_see_audit(db, audit_id, current_user)
        audit = self.audit_repo.get(db, audit_id)
        if not audit:
            raise NotFoundException("Audit not found.")
        return audit

    def get_audit_plan(self, db: Session, audit_plan_id: int, current_user: CurrentUser | None = None) -> AuditPlan:
        if current_user:
            assert_company_location_access(db, AuditPlan, audit_plan_id, current_user, not_found_detail="Audit plan not found.")
        audit_plan = self.audit_plan_repo.get(db, audit_plan_id)
        if not audit_plan:
            raise NotFoundException("Audit plan not found.")
        return audit_plan

    def create_audit_plan(self, db: Session, payload: AuditPlanCreate, actor_name: str, actor_id: int | None, current_user: CurrentUser | None = None) -> AuditPlan:
        data = payload.model_dump()
        self._reject_generated_references(data, {"audit_number"})
        if current_user:
            ensure_same_company_location(current_user=current_user, company_id=data.get("company_id"), location_id=data.get("location_id"))
        self._apply_audit_plan_period(data)
        self._validate_audit_plan_auditors(db, data)
        self._validate_date_range(data.get("start_date"), data.get("end_date"))
        data["created_by"] = actor_name
        data["updated_by"] = actor_name
        data["created_by_user_id"] = actor_id
        data["updated_by_user_id"] = actor_id
        audit_plan = self.audit_plan_repo.create(db, data)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type="audit_plan",
            entity_id=str(audit_plan.id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(audit_plan),
        )
        return audit_plan

    def update_audit_plan(self, db: Session, audit_plan_id: int, payload: AuditPlanUpdate, actor_name: str, actor_id: int | None, current_user: CurrentUser | None = None) -> AuditPlan:
        audit_plan = self.get_audit_plan(db, audit_plan_id, current_user)
        before = model_to_dict(audit_plan)
        data = payload.model_dump(exclude_unset=True)
        self._reject_generated_references(data, {"audit_number"})
        if audit_plan.approval_status == AuditPlanApprovalStatus.APPROVED.value and set(data) - {"remarks"}:
            raise ValidationException("Approved audit plans are locked. Only remarks can be updated.")
        if current_user:
            ensure_same_company_location(
                current_user=current_user,
                company_id=data.get("company_id", audit_plan.company_id),
                location_id=data.get("location_id", audit_plan.location_id),
            )
        if {"period_type", "period_value", "fiscal_year"} & set(data):
            self._apply_audit_plan_period(data, audit_plan)
        if {"audit_owner_id", "junior_auditor_1_id", "junior_auditor_2_id"} & set(data):
            self._validate_audit_plan_auditors(db, data, audit_plan)
        self._validate_date_range(data.get("start_date", audit_plan.start_date), data.get("end_date", audit_plan.end_date))
        data["updated_by"] = actor_name
        data["updated_by_user_id"] = actor_id
        audit_plan = self.audit_plan_repo.update(db, audit_plan, data)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type="audit_plan",
            entity_id=str(audit_plan.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=model_to_dict(audit_plan),
        )
        return audit_plan

    def _change_audit_plan_status(
        self,
        db: Session,
        audit_plan_id: int,
        target_status: str,
        *,
        actor_name: str,
        actor_id: int | None,
    ) -> AuditPlan:
        audit_plan = self.get_audit_plan(db, audit_plan_id)
        current_status = audit_plan.approval_status
        if target_status not in self.audit_plan_transitions.get(current_status, set()):
            raise ValidationException(f"Invalid audit plan approval transition from {current_status} to {target_status}.")
        before = model_to_dict(audit_plan)
        audit_plan.approval_status = target_status
        audit_plan.updated_by = actor_name
        audit_plan.updated_by_user_id = actor_id
        if target_status == AuditPlanApprovalStatus.APPROVED.value:
            audit_plan.approved_by_user_id = actor_id
            audit_plan.approved_at = datetime.now(UTC)
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type="audit_plan",
            entity_id=str(audit_plan.id),
            action_type=ActivityAction.STATUS_CHANGE.value if target_status != AuditPlanApprovalStatus.APPROVED.value else ActivityAction.APPROVE.value,
            old_values=before,
            new_values=model_to_dict(audit_plan),
        )
        return audit_plan

    def submit_audit_plan_for_approval(self, db: Session, audit_plan_id: int, actor_name: str, actor_id: int | None) -> AuditPlan:
        return self._change_audit_plan_status(
            db,
            audit_plan_id,
            AuditPlanApprovalStatus.UNDER_REVIEW.value,
            actor_name=actor_name,
            actor_id=actor_id,
        )

    def approve_audit_plan(self, db: Session, audit_plan_id: int, actor_name: str, actor_id: int | None) -> AuditPlan:
        return self._change_audit_plan_status(
            db,
            audit_plan_id,
            AuditPlanApprovalStatus.APPROVED.value,
            actor_name=actor_name,
            actor_id=actor_id,
        )

    def defer_audit_plan(self, db: Session, audit_plan_id: int, actor_name: str, actor_id: int | None) -> AuditPlan:
        return self._change_audit_plan_status(
            db,
            audit_plan_id,
            AuditPlanApprovalStatus.DEFERRED.value,
            actor_name=actor_name,
            actor_id=actor_id,
        )

    def cancel_audit_plan(self, db: Session, audit_plan_id: int, actor_name: str, actor_id: int | None) -> AuditPlan:
        return self._change_audit_plan_status(
            db,
            audit_plan_id,
            AuditPlanApprovalStatus.CANCELLED.value,
            actor_name=actor_name,
            actor_id=actor_id,
        )

    def _add_audit_membership(self, db: Session, *, audit_id: int, user_id: int | None, role_on_audit: str, actor_name: str, actor_id: int | None) -> None:
        if not user_id:
            return
        existing = db.scalar(
            select(AuditMembership).where(
                AuditMembership.audit_id == audit_id,
                AuditMembership.user_id == user_id,
                AuditMembership.role_on_audit == role_on_audit,
            )
        )
        if existing:
            existing.is_deleted = False
            existing.deleted_at = None
            existing.updated_by = actor_name
            existing.updated_by_user_id = actor_id
            db.flush()
            return
        db.add(
            AuditMembership(
                audit_id=audit_id,
                user_id=user_id,
                role_on_audit=role_on_audit,
                created_by=actor_name,
                updated_by=actor_name,
                created_by_user_id=actor_id,
                updated_by_user_id=actor_id,
            )
        )
        db.flush()

    def initiate_audit_from_plan(
        self,
        db: Session,
        audit_plan_id: int,
        payload: AuditPlanInitiateRequest,
        actor_name: str,
        actor_id: int | None,
    ) -> Audit:
        audit_plan = self.get_audit_plan(db, audit_plan_id)
        if audit_plan.approval_status != AuditPlanApprovalStatus.APPROVED.value:
            raise ValidationException("Only approved audit plans can be initiated.")
        existing_audit = db.scalar(select(Audit).where(Audit.audit_plan_id == audit_plan.id, Audit.is_deleted.is_(False)))
        if existing_audit:
            return existing_audit
        owner_id = audit_plan.audit_owner_id
        if not owner_id:
            raise ValidationException("Assign a Lead Auditor in the Audit Plan before initiating the audit.")
        assignment_directory_service.validate_internal_user(db, owner_id, "Lead Auditor")
        data = payload.model_dump(exclude_none=True)
        self._validate_audit_people(db, data)
        reviewer_user_id = data.get("reviewer_user_id")
        auditee_spoc_user_id = data.get("auditee_spoc_user_id")
        auditee_spoc_auditee_id = data.get("auditee_spoc_auditee_id")
        junior_auditor_user_ids = [user_id for user_id in (audit_plan.junior_auditor_1_id, audit_plan.junior_auditor_2_id) if user_id]
        assignment_entry = {
            "action": "initiated_from_plan",
            "by": actor_name,
            "at": datetime.now(UTC).isoformat(),
            "audit_owner_id": owner_id,
            "reviewer_user_id": reviewer_user_id,
            "auditee_spoc_user_id": auditee_spoc_user_id,
            "auditee_spoc_auditee_id": auditee_spoc_auditee_id,
            "junior_auditor_user_ids": junior_auditor_user_ids,
        }
        audit = Audit(
            audit_plan_id=audit_plan.id,
            audit_name=audit_plan.audit_name,
            company_id=audit_plan.company_id,
            location_id=audit_plan.location_id,
            quarter=audit_plan.quarter,
            period_type=audit_plan.period_type,
            period_value=audit_plan.period_value,
            fiscal_year=audit_plan.fiscal_year,
            start_date=audit_plan.start_date,
            end_date=audit_plan.end_date,
            status=AuditStatus.TO_BE_INITIATED.value,
            planned_flag=audit_plan.planned_flag,
            criticality=audit_plan.criticality,
            audit_owner_id=owner_id,
            reviewer_user_id=reviewer_user_id,
            auditee_spoc_auditee_id=auditee_spoc_auditee_id,
            auditee_spoc_user_id=auditee_spoc_user_id,
            remarks=audit_plan.remarks,
            history_timeline=[{"status": AuditStatus.TO_BE_INITIATED.value, "note": "Initiated from approved audit plan", "by": actor_name}],
            assignment_history=[assignment_entry],
            created_by=actor_name,
            updated_by=actor_name,
            created_by_user_id=actor_id,
            updated_by_user_id=actor_id,
        )
        db.add(audit)
        db.flush()
        db.refresh(audit)
        self._add_audit_membership(db, audit_id=audit.id, user_id=owner_id, role_on_audit=AuditMembershipRole.LEAD_AUDITOR.value, actor_name=actor_name, actor_id=actor_id)
        self._add_audit_membership(db, audit_id=audit.id, user_id=reviewer_user_id, role_on_audit=AuditMembershipRole.REVIEWER.value, actor_name=actor_name, actor_id=actor_id)
        self._add_audit_membership(db, audit_id=audit.id, user_id=auditee_spoc_user_id, role_on_audit=AuditMembershipRole.AUDITEE_SPOC.value, actor_name=actor_name, actor_id=actor_id)
        for junior_id in junior_auditor_user_ids:
            self._add_audit_membership(db, audit_id=audit.id, user_id=junior_id, role_on_audit=AuditMembershipRole.JUNIOR_AUDITOR.value, actor_name=actor_name, actor_id=actor_id)
        audit_event_service.record(
            db,
            audit=audit,
            event_type=AuditEventType.AUDIT_INITIATED,
            event_title="Audit initiated",
            actor_name=actor_name,
            actor_id=actor_id,
            description="Audit created from approved audit plan.",
            to_status=AuditStatus.TO_BE_INITIATED.value,
            payload={"audit_plan_id": audit_plan.id, "assignment_history": assignment_entry},
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
            new_values={"audit": model_to_dict(audit), "initiated_from_audit_plan_id": audit_plan.id},
        )
        activity_log_service.notify(
            db,
            user_id=owner_id,
            title="Audit initiated",
            message=f"{audit.audit_number} is ready for engagement planning.",
            actor_user_id=actor_id,
            actor_name=actor_name,
            payload={
                "audit_id": audit.id,
                "audit_number": audit.audit_number,
                "audit_plan_id": audit_plan.id,
                "event": "audit_initiated",
            },
        )
        return audit

    def _ensure_audit_plan_can_be_deleted(self, db: Session, audit_plan: AuditPlan) -> None:
        if audit_plan.audit and not audit_plan.audit.is_deleted:
            raise ConflictException("This audit plan cannot be deleted because it is linked to an active audit.")
        if any(not record.is_deleted for record in audit_plan.process_risk_mappings):
            raise ConflictException("This audit plan cannot be deleted because it has active process risk mappings.")
        if any(not record.is_deleted for record in audit_plan.erm_risks):
            raise ConflictException("This audit plan cannot be deleted because it has active ERM risks.")
        if any(not record.is_deleted for record in audit_plan.business_initiatives):
            raise ConflictException("This audit plan cannot be deleted because it has active business initiatives.")
        if any(not record.is_deleted for record in audit_plan.overall_assessments):
            raise ConflictException("This audit plan cannot be deleted because it has active overall assessments.")

    def delete_audit_plan(self, db: Session, audit_plan_id: int, actor_name: str, actor_id: int | None) -> None:
        audit_plan = self.get_audit_plan(db, audit_plan_id)
        self._ensure_audit_plan_can_be_deleted(db, audit_plan)
        before = model_to_dict(audit_plan)
        self.audit_plan_repo.soft_delete(db, audit_plan, actor_name=actor_name)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type="audit_plan",
            entity_id=str(audit_plan.id),
            action_type=ActivityAction.DELETE.value,
            old_values=before,
            new_values={"is_deleted": True},
        )

    def bulk_delete_audit_plans(self, db: Session, ids: list[int], actor_name: str, actor_id: int | None) -> BulkDeleteResponse:
        deleted_ids: list[int] = []
        blocked: list[BlockedDeleteItem] = []
        for audit_plan_id in ids:
            try:
                self.delete_audit_plan(db, audit_plan_id, actor_name, actor_id)
                deleted_ids.append(audit_plan_id)
            except (ConflictException, NotFoundException) as exc:
                blocked.append(BlockedDeleteItem(id=audit_plan_id, reason=str(exc.detail)))
        response = BulkDeleteResponse(
            deleted_ids=deleted_ids,
            blocked=blocked,
            message=(
                f"Deleted {len(deleted_ids)} record(s)." if deleted_ids and not blocked else
                f"Deleted {len(deleted_ids)} record(s); {len(blocked)} record(s) were blocked by dependencies." if deleted_ids else
                "No records were deleted."
            ),
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type="audit_plan",
            entity_id="bulk",
            action_type=ActivityAction.DELETE.value,
            new_values=response.model_dump(),
        )
        return response

    def create_audit(self, db: Session, payload: AuditCreate, actor_name: str, actor_id: int | None) -> Audit:
        data = payload.model_dump()
        self._reject_generated_references(data, {"audit_number"})
        self._apply_audit_period_compatibility(data)
        self._validate_audit_people(db, data)
        self._validate_date_range(data.get("start_date"), data.get("end_date"))
        data["created_by"] = actor_name
        data["updated_by"] = actor_name
        data["created_by_user_id"] = actor_id
        data["updated_by_user_id"] = actor_id
        audit = self.audit_repo.create(db, data)
        audit_event_service.record(
            db,
            audit=audit,
            event_type=AuditEventType.AUDIT_INITIATED,
            event_title="Audit created",
            actor_name=actor_name,
            actor_id=actor_id,
            description="Audit record created directly.",
            to_status=audit.status,
            payload=model_to_dict(audit),
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
            new_values=model_to_dict(audit),
        )
        return audit

    def update_audit(self, db: Session, audit_id: int, payload: AuditUpdate, actor_name: str, actor_id: int | None) -> Audit:
        audit = self.get_audit(db, audit_id)
        before = model_to_dict(audit)
        data = payload.model_dump(exclude_none=True)
        self._reject_generated_references(data, {"audit_number"})
        self._apply_audit_period_compatibility(data, audit)
        self._validate_audit_people(db, data, audit)
        self._validate_date_range(data.get("start_date", audit.start_date), data.get("end_date", audit.end_date))
        if data.get("status") == AuditStatus.COMPLETED.value and not audit.action_plans:
            history = list(audit.history_timeline or [])
            history.append({"status": AuditStatus.COMPLETED.value, "note": "Completed without linked action plans", "by": actor_name})
            data["history_timeline"] = history
        data["updated_by"] = actor_name
        data["updated_by_user_id"] = actor_id
        audit = self.audit_repo.update(db, audit, data)
        if "status" in data:
            audit_event_service.record(
                db,
                audit=audit,
                event_type=AuditEventType.STATUS_CHANGED,
                event_title="Audit status changed",
                actor_name=actor_name,
                actor_id=actor_id,
                description=data.get("remarks") or audit.remarks,
                from_status=before.get("status"),
                to_status=audit.status,
                payload={"audit_id": audit.id},
            )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="audits",
            entity_type="audit",
            entity_id=str(audit.id),
            action_type=ActivityAction.UPDATE.value if "status" not in data else ActivityAction.STATUS_CHANGE.value,
            old_values=before,
            new_values=model_to_dict(audit),
        )
        return audit

    def list_members(self, db: Session, audit_id: int, current_user: CurrentUser) -> list[AuditMembership]:
        assert_can_see_audit(db, audit_id, current_user)
        return list(
            db.scalars(
                select(AuditMembership)
                .options(joinedload(AuditMembership.user))
                .where(AuditMembership.audit_id == audit_id, AuditMembership.is_deleted.is_(False))
                .order_by(AuditMembership.role_on_audit, AuditMembership.id)
            ).all()
        )

    def add_member(self, db: Session, audit_id: int, payload: AuditMembershipCreate, actor_name: str, actor_id: int | None) -> AuditMembership:
        audit = self.get_audit(db, audit_id)
        if payload.role_on_audit not in {role.value for role in AuditMembershipRole}:
            raise ValidationException("Invalid audit membership role.")
        assignment_directory_service.validate_internal_user(db, payload.user_id, "Audit member")
        self._add_audit_membership(db, audit_id=audit.id, user_id=payload.user_id, role_on_audit=payload.role_on_audit, actor_name=actor_name, actor_id=actor_id)
        membership = db.scalar(
            select(AuditMembership).where(
                AuditMembership.audit_id == audit.id,
                AuditMembership.user_id == payload.user_id,
                AuditMembership.role_on_audit == payload.role_on_audit,
                AuditMembership.is_deleted.is_(False),
            )
        )
        history = list(audit.assignment_history or [])
        history.append({"action": "member_added", "user_id": payload.user_id, "role_on_audit": payload.role_on_audit, "by": actor_name, "at": datetime.now(UTC).isoformat()})
        audit.assignment_history = history
        audit.updated_by = actor_name
        audit.updated_by_user_id = actor_id
        audit_event_service.record(
            db,
            audit=audit,
            event_type=AuditEventType.MEMBER_ASSIGNED,
            event_title="Audit member assigned",
            actor_name=actor_name,
            actor_id=actor_id,
            description=f"User {payload.user_id} added as {payload.role_on_audit}.",
            payload={"membership": model_to_dict(membership)},
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="audits",
            entity_type="audit_membership",
            entity_id=str(membership.id),
            action_type=ActivityAction.ASSIGN.value,
            new_values=model_to_dict(membership),
        )
        return membership

    def remove_member(self, db: Session, audit_id: int, membership_id: int, actor_name: str, actor_id: int | None) -> None:
        self.get_audit(db, audit_id)
        membership = db.scalar(
            select(AuditMembership).where(
                AuditMembership.id == membership_id,
                AuditMembership.audit_id == audit_id,
                AuditMembership.is_deleted.is_(False),
            )
        )
        if not membership:
            raise NotFoundException("Audit membership not found.")
        before = model_to_dict(membership)
        self.membership_repo.soft_delete(db, membership, actor_name=actor_name)
        membership.updated_by_user_id = actor_id
        audit = self.get_audit(db, audit_id)
        audit_event_service.record(
            db,
            audit=audit,
            event_type=AuditEventType.MEMBER_REMOVED,
            event_title="Audit member removed",
            actor_name=actor_name,
            actor_id=actor_id,
            description=f"User {membership.user_id} removed from audit membership.",
            payload={"membership": before},
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="audits",
            entity_type="audit_membership",
            entity_id=str(membership.id),
            action_type=ActivityAction.DELETE.value,
            old_values=before,
            new_values={"is_deleted": True},
        )

    def completion(self, db: Session, audit_id: int, current_user: CurrentUser) -> dict[str, int | float]:
        assert_can_see_audit(db, audit_id, current_user)
        row = db.execute(
            select(
                func.count(AuditActivity.id),
                func.sum(case((AuditActivity.status == "Completed", 1), else_=0)),
            ).where(
                AuditActivity.audit_id == audit_id,
                AuditActivity.status != "Not Applicable",
                AuditActivity.is_deleted.is_(False),
            )
        ).one()
        total = int(row[0] or 0)
        completed = int(row[1] or 0)
        return {"completed": completed, "total": total, "percentage": round(100 * completed / total, 1) if total else 0.0}

    def delete_audit(self, db: Session, audit_id: int, actor_name: str, actor_id: int | None) -> None:
        audit = self.get_audit(db, audit_id)
        active_action_plan = db.scalar(select(ActionPlan.id).where(ActionPlan.audit_id == audit_id, ActionPlan.is_deleted.is_(False)).limit(1))
        if active_action_plan:
            raise ConflictException("This audit cannot be deleted because it still has active action plans.")
        before = model_to_dict(audit)
        self.audit_repo.soft_delete(db, audit, actor_name=actor_name)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="audits",
            entity_type="audit",
            entity_id=str(audit.id),
            action_type=ActivityAction.DELETE.value,
            old_values=before,
            new_values={"is_deleted": True},
        )

    def bulk_delete_audits(self, db: Session, ids: list[int], actor_name: str, actor_id: int | None) -> BulkDeleteResponse:
        deleted_ids: list[int] = []
        blocked: list[BlockedDeleteItem] = []
        for audit_id in ids:
            try:
                self.delete_audit(db, audit_id, actor_name, actor_id)
                deleted_ids.append(audit_id)
            except (ConflictException, NotFoundException) as exc:
                blocked.append(BlockedDeleteItem(id=audit_id, reason=str(exc.detail)))
        response = BulkDeleteResponse(
            deleted_ids=deleted_ids,
            blocked=blocked,
            message=(
                f"Deleted {len(deleted_ids)} record(s)." if deleted_ids and not blocked else
                f"Deleted {len(deleted_ids)} record(s); {len(blocked)} record(s) were blocked by dependencies." if deleted_ids else
                "No records were deleted."
            ),
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="audits",
            entity_type="audit",
            entity_id="bulk",
            action_type=ActivityAction.DELETE.value,
            new_values=response.model_dump(),
        )
        return response


audit_service = AuditService()
