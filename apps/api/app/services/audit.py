from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction, AuditStatus
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.action_plan import ActionPlan
from app.models.audit import Audit, AuditPlan
from app.repositories.base import BaseRepository
from app.schemas.audit import AuditCreate, AuditPlanCreate, AuditPlanUpdate, AuditUpdate
from app.schemas.common import BlockedDeleteItem, BulkDeleteResponse, ListQuery, PaginationMeta, PaginatedResponse
from app.services.activity_log import activity_log_service
from app.utils.serialization import model_to_dict


class AuditService:
    audit_repo = BaseRepository(Audit)
    audit_plan_repo = BaseRepository(AuditPlan)
    period_values = {
        "Quarterly": {"Q1", "Q2", "Q3", "Q4"},
        "Half-Yearly": {"H1", "H2"},
        "Annual": {"Full Year"},
    }
    fiscal_years = {f"{year}-{year + 1}" for year in range(2025, 2043)}

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
            raise ValidationException("Period Type must be Quarterly, Half-Yearly, or Annual.")
        if period_value not in self.period_values[period_type]:
            raise ValidationException("Period Value must match the selected Period Type.")
        return period_type, period_value

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
        has_period_input = "period_type" in data or "period_value" in data
        if has_period_input:
            inferred = self._period_from_value(existing.quarter if existing else data.get("quarter"))
            current_type = existing.period_type if existing and existing.period_type else inferred[0] if inferred else None
            current_value = existing.period_value if existing and existing.period_value else inferred[1] if inferred else None
            period_type = data.get("period_type", current_type)
            period_value = data.get("period_value", current_value)
            period_type, period_value = self._validate_period_pair(period_type, period_value)
            data["period_type"] = period_type
            data["period_value"] = period_value
            data["quarter"] = period_value
            return

        if "quarter" in data:
            inferred = self._period_from_value(data.get("quarter"))
            if inferred:
                data["period_type"], data["period_value"] = inferred

    def list_audits(self, db: Session, query: ListQuery) -> PaginatedResponse[Audit]:
        items, total = self.audit_repo.list(
            db,
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            search_fields=["audit_number", "audit_name", "status", "quarter", "period_type", "period_value", "fiscal_year"],
            filters=query.filters,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        return PaginatedResponse(items=items, meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def list_audit_plans(self, db: Session, query: ListQuery) -> PaginatedResponse[AuditPlan]:
        items, total = self.audit_plan_repo.list(
            db,
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            search_fields=["audit_number", "audit_name", "quarter", "period_type", "period_value", "fiscal_year"],
            filters=query.filters,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        return PaginatedResponse(items=items, meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def get_audit(self, db: Session, audit_id: int) -> Audit:
        audit = self.audit_repo.get(db, audit_id)
        if not audit:
            raise NotFoundException("Audit not found.")
        return audit

    def get_audit_plan(self, db: Session, audit_plan_id: int) -> AuditPlan:
        audit_plan = self.audit_plan_repo.get(db, audit_plan_id)
        if not audit_plan:
            raise NotFoundException("Audit plan not found.")
        return audit_plan

    def create_audit_plan(self, db: Session, payload: AuditPlanCreate, actor_name: str, actor_id: int | None) -> AuditPlan:
        data = payload.model_dump()
        self._reject_generated_references(data, {"audit_number"})
        self._apply_audit_plan_period(data)
        self._validate_date_range(data.get("start_date"), data.get("end_date"))
        data["created_by"] = actor_name
        data["updated_by"] = actor_name
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

    def update_audit_plan(self, db: Session, audit_plan_id: int, payload: AuditPlanUpdate, actor_name: str, actor_id: int | None) -> AuditPlan:
        audit_plan = self.get_audit_plan(db, audit_plan_id)
        before = model_to_dict(audit_plan)
        data = payload.model_dump(exclude_none=True)
        self._reject_generated_references(data, {"audit_number"})
        if {"period_type", "period_value", "fiscal_year"} & set(data):
            self._apply_audit_plan_period(data, audit_plan)
        self._validate_date_range(data.get("start_date", audit_plan.start_date), data.get("end_date", audit_plan.end_date))
        data["updated_by"] = actor_name
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
        self._validate_date_range(data.get("start_date"), data.get("end_date"))
        data["created_by"] = actor_name
        data["updated_by"] = actor_name
        audit = self.audit_repo.create(db, data)
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
        self._validate_date_range(data.get("start_date", audit.start_date), data.get("end_date", audit.end_date))
        if data.get("status") == AuditStatus.COMPLETED.value and not audit.action_plans:
            history = list(audit.history_timeline or [])
            history.append({"status": AuditStatus.COMPLETED.value, "note": "Completed without linked action plans", "by": actor_name})
            data["history_timeline"] = history
        data["updated_by"] = actor_name
        audit = self.audit_repo.update(db, audit, data)
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
