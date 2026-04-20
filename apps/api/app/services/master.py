from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.inspection import inspect as sqlalchemy_inspect
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.permissions import MASTER_RESOURCE_MAP
from app.models import (
    ActionPlan,
    Audit,
    AuditEscalation,
    AuditPlan,
    BusinessInitiative,
    City,
    Company,
    ControlPerformanceIndicator,
    Country,
    Designation,
    ERMRisk,
    Impact,
    Location,
    ObservationGrading,
    OverallAssessment,
    Process,
    ProcessLocationMapping,
    ProcessRiskMapping,
    Recommendation,
    ReportConsideration,
    RiskType,
    RootCause,
    State,
    TaskSwapRule,
    TrialBalance,
    User,
)
from app.repositories.base import BaseRepository
from app.schemas.common import BlockedDeleteItem, BulkDeleteResponse, ListQuery, PaginationMeta, PaginatedResponse
from app.schemas.master import MasterRecordCreate, MasterRecordUpdate
from app.services.activity_log import activity_log_service
from app.utils.serialization import model_to_dict

MASTER_MODELS: dict[str, type] = {
    "countries": Country,
    "states": State,
    "cities": City,
    "companies": Company,
    "processes": Process,
    "locations": Location,
    "process-location-mappings": ProcessLocationMapping,
    "risk-types": RiskType,
    "report-considerations": ReportConsideration,
    "recommendations": Recommendation,
    "root-causes": RootCause,
    "impacts": Impact,
    "trial-balances": TrialBalance,
    "observation-gradings": ObservationGrading,
    "audit-escalations": AuditEscalation,
    "designations": Designation,
    "control-performance-indicators": ControlPerformanceIndicator,
    "task-swaps": TaskSwapRule,
}

MASTER_DEPENDENCY_CHECKS: dict[str, list[tuple[type, str, str]]] = {
    "countries": [(State, "country_id", "states"), (Company, "country_id", "companies"), (Location, "country_id", "locations")],
    "states": [(City, "state_id", "cities"), (Company, "state_id", "companies"), (Location, "state_id", "locations")],
    "cities": [(Company, "city_id", "companies"), (Location, "city_id", "locations")],
    "companies": [
        (Location, "company_id", "locations"),
        (User, "company_id", "users"),
        (AuditPlan, "company_id", "audit plans"),
        (Audit, "company_id", "audits"),
        (ProcessLocationMapping, "company_id", "process-location mappings"),
        (TrialBalance, "company_id", "trial balances"),
    ],
    "processes": [(ProcessLocationMapping, "process_id", "process-location mappings"), (ERMRisk, "process_id", "ERM risks")],
    "locations": [
        (User, "location_id", "users"),
        (AuditPlan, "location_id", "audit plans"),
        (Audit, "location_id", "audits"),
        (ActionPlan, "location_id", "action plans"),
        (ProcessLocationMapping, "location_id", "process-location mappings"),
        (OverallAssessment, "location_id", "overall assessments"),
    ],
    "process-location-mappings": [(ProcessRiskMapping, "process_location_mapping_id", "process risk mappings")],
    "risk-types": [(ActionPlan, "risk_type_id", "action plans")],
    "root-causes": [(ActionPlan, "root_cause_id", "action plans")],
    "trial-balances": [(ProcessLocationMapping, "trial_balance_id", "process-location mappings"), (ProcessRiskMapping, "trial_balance_id", "process risk mappings")],
    "observation-gradings": [(ActionPlan, "observation_grading_id", "action plans")],
    "designations": [(User, "designation_id", "users"), (TaskSwapRule, "source_designation_id", "task swap rules"), (TaskSwapRule, "target_designation_id", "task swap rules")],
}


class MasterService:
    def _get_model(self, resource: str) -> type:
        model = MASTER_MODELS.get(resource)
        if not model:
            raise NotFoundException(f"Master resource '{resource}' is not supported.")
        return model

    def _get_repository(self, resource: str) -> BaseRepository:
        return BaseRepository(self._get_model(resource))

    def _filter_payload(self, model: type, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = {column.key for column in sqlalchemy_inspect(model).columns}
        filtered = {key: value for key, value in payload.items() if key in allowed}
        if model is Company and "name" not in filtered and payload.get("title"):
            filtered["name"] = payload["title"]
        if model is Designation and "title" not in filtered and payload.get("name"):
            filtered["title"] = payload["name"]
        if model is Process and "name" not in filtered and payload.get("title"):
            filtered["name"] = payload["title"]
        return filtered

    def _as_int(self, value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _validate_geography_chain(self, db: Session, model: type, data: dict[str, Any]) -> None:
        if model not in {Company, Location}:
            return

        country_id = self._as_int(data.get("country_id"))
        state_id = self._as_int(data.get("state_id"))
        city_id = self._as_int(data.get("city_id"))

        if country_id and state_id:
            state_country_id = db.scalar(
                select(State.country_id).where(
                    State.id == state_id,
                    State.is_deleted.is_(False),
                )
            )
            if state_country_id is None:
                raise ValidationException("Selected state was not found.")
            if state_country_id != country_id:
                raise ValidationException("Selected state does not belong to the selected country.")

        if state_id and city_id:
            city_state_id = db.scalar(
                select(City.state_id).where(
                    City.id == city_id,
                    City.is_deleted.is_(False),
                )
            )
            if city_state_id is None:
                raise ValidationException("Selected city was not found.")
            if city_state_id != state_id:
                raise ValidationException("Selected city does not belong to the selected state.")

    def _ensure_not_referenced(self, db: Session, resource: str, entity_id: int) -> None:
        for model, field_name, label in MASTER_DEPENDENCY_CHECKS.get(resource, []):
            dependent_id = db.scalar(select(model.id).where(getattr(model, field_name) == entity_id, model.is_deleted.is_(False)).limit(1))
            if dependent_id:
                raise ConflictException(f"This record cannot be deleted because it is still referenced by active {label}.")

    def _build_bulk_message(self, deleted_ids: list[int], blocked: list[BlockedDeleteItem]) -> str:
        if deleted_ids and not blocked:
            return f"Deleted {len(deleted_ids)} record(s)."
        if deleted_ids and blocked:
            return f"Deleted {len(deleted_ids)} record(s); {len(blocked)} record(s) were blocked by dependencies."
        return "No records were deleted."

    def list(self, db: Session, resource: str, query: ListQuery) -> PaginatedResponse[Any]:
        model = self._get_model(resource)
        repository = BaseRepository(model)
        search_fields: list[str] = []
        for column in sqlalchemy_inspect(model).columns:
            try:
                if column.type.python_type is str:
                    search_fields.append(column.key)
            except NotImplementedError:
                continue
        items, total = repository.list(
            db,
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            search_fields=search_fields[:4],
            filters=query.filters,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        return PaginatedResponse(items=items, meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def create(self, db: Session, resource: str, payload: MasterRecordCreate, actor_name: str, actor_id: int | None) -> Any:
        model = self._get_model(resource)
        repository = BaseRepository(model)
        data = self._filter_payload(model, payload.model_dump(exclude_none=True))
        if not data:
            raise ValidationException("Payload does not contain any supported fields for this resource.")
        self._validate_geography_chain(db, model, data)
        data["created_by"] = actor_name
        data["updated_by"] = actor_name
        entity = repository.create(db, data)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="master",
            entity_type=MASTER_RESOURCE_MAP[resource],
            entity_id=str(entity.id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(entity),
        )
        return entity

    def update(self, db: Session, resource: str, entity_id: int, payload: MasterRecordUpdate, actor_name: str, actor_id: int | None) -> Any:
        model = self._get_model(resource)
        repository = BaseRepository(model)
        entity = repository.get(db, entity_id)
        if not entity:
            raise NotFoundException("Master record not found.")
        before = model_to_dict(entity)
        data = self._filter_payload(model, payload.model_dump(exclude_none=True))
        self._validate_geography_chain(db, model, {**before, **data})
        data["updated_by"] = actor_name
        entity = repository.update(db, entity, data)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="master",
            entity_type=MASTER_RESOURCE_MAP[resource],
            entity_id=str(entity.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=model_to_dict(entity),
        )
        return entity

    def delete(self, db: Session, resource: str, entity_id: int, actor_name: str, actor_id: int | None) -> None:
        repository = self._get_repository(resource)
        entity = repository.get(db, entity_id)
        if not entity:
            raise NotFoundException("Master record not found.")
        self._ensure_not_referenced(db, resource, entity_id)
        before = model_to_dict(entity)
        repository.soft_delete(db, entity, actor_name=actor_name)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="master",
            entity_type=MASTER_RESOURCE_MAP[resource],
            entity_id=str(entity.id),
            action_type=ActivityAction.DELETE.value,
            old_values=before,
            new_values={"is_deleted": True},
        )

    def bulk_delete(self, db: Session, resource: str, ids: list[int], actor_name: str, actor_id: int | None) -> BulkDeleteResponse:
        deleted_ids: list[int] = []
        blocked: list[BlockedDeleteItem] = []
        for entity_id in ids:
            try:
                self.delete(db, resource, entity_id, actor_name, actor_id)
                deleted_ids.append(entity_id)
            except (ConflictException, NotFoundException) as exc:
                blocked.append(BlockedDeleteItem(id=entity_id, reason=str(exc.detail)))
        response = BulkDeleteResponse(deleted_ids=deleted_ids, blocked=blocked, message=self._build_bulk_message(deleted_ids, blocked))
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="master",
            entity_type=MASTER_RESOURCE_MAP[resource],
            entity_id="bulk",
            action_type=ActivityAction.DELETE.value,
            new_values=response.model_dump(),
        )
        return response


master_service = MasterService()
