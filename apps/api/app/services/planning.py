from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import ActivityAction
from app.core.exceptions import NotFoundException
from app.models.audit import BusinessInitiative, ERMRisk, OverallAssessment, ProcessRiskMapping
from app.repositories.base import BaseRepository
from app.schemas.common import BlockedDeleteItem, BulkDeleteResponse, ListQuery, PaginationMeta, PaginatedResponse
from app.services.activity_log import activity_log_service
from app.utils.serialization import model_to_dict

PLANNING_MODELS: dict[str, type] = {
    "process-risk-mappings": ProcessRiskMapping,
    "erm-risks": ERMRisk,
    "business-initiatives": BusinessInitiative,
    "overall-assessments": OverallAssessment,
}

PLANNING_SEARCH_FIELDS: dict[str, list[str]] = {
    "process-risk-mappings": ["quantitative_assessment", "qualitative_assessment", "final_process_rating"],
    "erm-risks": ["erm_risk_code", "erm_risk_title", "description"],
    "business-initiatives": ["initiative_code", "title", "description"],
    "overall-assessments": ["overall_risk", "coverage_status", "justification"],
}


class PlanningService:
    def _repo(self, resource: str) -> BaseRepository:
        model = PLANNING_MODELS.get(resource)
        if not model:
            raise NotFoundException(f"Unsupported planning resource '{resource}'.")
        return BaseRepository(model)

    def list(self, db: Session, resource: str, query: ListQuery) -> PaginatedResponse[Any]:
        repo = self._repo(resource)
        items, total = repo.list(
            db,
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            search_fields=PLANNING_SEARCH_FIELDS.get(resource, []),
            filters=query.filters,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        return PaginatedResponse(items=items, meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def create(self, db: Session, resource: str, payload: dict[str, Any], actor_name: str, actor_id: int | None) -> Any:
        repo = self._repo(resource)
        payload["created_by"] = actor_name
        payload["updated_by"] = actor_name
        entity = repo.create(db, payload)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type=resource,
            entity_id=str(entity.id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(entity),
        )
        return entity

    def update(self, db: Session, resource: str, entity_id: int, payload: dict[str, Any], actor_name: str, actor_id: int | None) -> Any:
        repo = self._repo(resource)
        entity = repo.get(db, entity_id)
        if not entity:
            raise NotFoundException("Planning record not found.")
        before = model_to_dict(entity)
        payload["updated_by"] = actor_name
        entity = repo.update(db, entity, payload)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type=resource,
            entity_id=str(entity.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=model_to_dict(entity),
        )
        return entity

    def delete(self, db: Session, resource: str, entity_id: int, actor_name: str, actor_id: int | None) -> None:
        repo = self._repo(resource)
        entity = repo.get(db, entity_id)
        if not entity:
            raise NotFoundException("Planning record not found.")
        before = model_to_dict(entity)
        repo.soft_delete(db, entity, actor_name=actor_name)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type=resource,
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
            except NotFoundException as exc:
                blocked.append(BlockedDeleteItem(id=entity_id, reason=str(exc.detail)))
        message = (
            f"Deleted {len(deleted_ids)} record(s)." if deleted_ids and not blocked else
            f"Deleted {len(deleted_ids)} record(s); {len(blocked)} record(s) could not be deleted." if deleted_ids else
            "No records were deleted."
        )
        response = BulkDeleteResponse(deleted_ids=deleted_ids, blocked=blocked, message=message)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type=resource,
            entity_id="bulk",
            action_type=ActivityAction.DELETE.value,
            new_values=response.model_dump(),
        )
        return response


planning_service = PlanningService()
