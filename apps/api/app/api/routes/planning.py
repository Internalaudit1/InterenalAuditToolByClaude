from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.api.deps.common import get_list_query
from app.db.session import get_db
from app.schemas.audit import AuditPlanCreate, AuditPlanResponse, AuditPlanUpdate
from app.schemas.common import BulkDeleteRequest, BulkDeleteResponse, ListQuery, MessageResponse, PaginatedResponse
from app.schemas.planning import (
    BusinessInitiativeCreate,
    BusinessInitiativeResponse,
    BusinessInitiativeUpdate,
    ERMRiskCreate,
    ERMRiskResponse,
    ERMRiskUpdate,
    OverallAssessmentCreate,
    OverallAssessmentResponse,
    OverallAssessmentUpdate,
    ProcessRiskMappingCreate,
    ProcessRiskMappingResponse,
    ProcessRiskMappingUpdate,
)
from app.services.audit import audit_service
from app.services.planning import planning_service

router = APIRouter(prefix="/planning", tags=["planning"])


@router.get("/process-risk-mappings", response_model=PaginatedResponse[ProcessRiskMappingResponse])
def list_process_risk_mappings(
    query: Annotated[ListQuery, Depends(get_list_query)],
    audit_plan_id: int | None = Query(None),
    _: CurrentUser = Depends(require_permissions("planning:view")),
    db: Session = Depends(get_db),
):
    query.filters = {"audit_plan_id": audit_plan_id} if audit_plan_id else None
    return planning_service.list(db, "process-risk-mappings", query)


@router.post("/process-risk-mappings", response_model=ProcessRiskMappingResponse)
def create_process_risk_mapping(
    payload: ProcessRiskMappingCreate,
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    entity = planning_service.create(db, "process-risk-mappings", payload.model_dump(), current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.put("/process-risk-mappings/{entity_id}", response_model=ProcessRiskMappingResponse)
def update_process_risk_mapping(
    entity_id: int,
    payload: ProcessRiskMappingUpdate,
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    entity = planning_service.update(db, "process-risk-mappings", entity_id, payload.model_dump(exclude_none=True), current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.delete("/process-risk-mappings/{entity_id}", response_model=MessageResponse)
def delete_process_risk_mapping(
    entity_id: int,
    current_user: CurrentUser = Depends(require_permissions("planning:delete")),
    db: Session = Depends(get_db),
):
    planning_service.delete(db, "process-risk-mappings", entity_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="Process risk mapping deleted.")


@router.post("/process-risk-mappings/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_process_risk_mappings(
    payload: BulkDeleteRequest,
    current_user: CurrentUser = Depends(require_permissions("planning:delete")),
    db: Session = Depends(get_db),
):
    response = planning_service.bulk_delete(db, "process-risk-mappings", payload.ids, current_user.full_name, current_user.id)
    db.commit()
    return response


@router.get("/erm-risks", response_model=PaginatedResponse[ERMRiskResponse])
def list_erm_risks(
    query: Annotated[ListQuery, Depends(get_list_query)],
    audit_plan_id: int | None = Query(None),
    _: CurrentUser = Depends(require_permissions("planning:view")),
    db: Session = Depends(get_db),
):
    query.filters = {"audit_plan_id": audit_plan_id} if audit_plan_id else None
    return planning_service.list(db, "erm-risks", query)


@router.post("/erm-risks", response_model=ERMRiskResponse)
def create_erm_risk(
    payload: ERMRiskCreate,
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    entity = planning_service.create(db, "erm-risks", payload.model_dump(), current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.put("/erm-risks/{entity_id}", response_model=ERMRiskResponse)
def update_erm_risk(
    entity_id: int,
    payload: ERMRiskUpdate,
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    entity = planning_service.update(db, "erm-risks", entity_id, payload.model_dump(exclude_none=True), current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.delete("/erm-risks/{entity_id}", response_model=MessageResponse)
def delete_erm_risk(
    entity_id: int,
    current_user: CurrentUser = Depends(require_permissions("planning:delete")),
    db: Session = Depends(get_db),
):
    planning_service.delete(db, "erm-risks", entity_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="ERM risk deleted.")


@router.post("/erm-risks/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_erm_risks(
    payload: BulkDeleteRequest,
    current_user: CurrentUser = Depends(require_permissions("planning:delete")),
    db: Session = Depends(get_db),
):
    response = planning_service.bulk_delete(db, "erm-risks", payload.ids, current_user.full_name, current_user.id)
    db.commit()
    return response


@router.get("/business-initiatives", response_model=PaginatedResponse[BusinessInitiativeResponse])
def list_business_initiatives(
    query: Annotated[ListQuery, Depends(get_list_query)],
    audit_plan_id: int | None = Query(None),
    _: CurrentUser = Depends(require_permissions("planning:view")),
    db: Session = Depends(get_db),
):
    query.filters = {"audit_plan_id": audit_plan_id} if audit_plan_id else None
    return planning_service.list(db, "business-initiatives", query)


@router.post("/business-initiatives", response_model=BusinessInitiativeResponse)
def create_business_initiative(
    payload: BusinessInitiativeCreate,
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    entity = planning_service.create(db, "business-initiatives", payload.model_dump(), current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.put("/business-initiatives/{entity_id}", response_model=BusinessInitiativeResponse)
def update_business_initiative(
    entity_id: int,
    payload: BusinessInitiativeUpdate,
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    entity = planning_service.update(db, "business-initiatives", entity_id, payload.model_dump(exclude_none=True), current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.delete("/business-initiatives/{entity_id}", response_model=MessageResponse)
def delete_business_initiative(
    entity_id: int,
    current_user: CurrentUser = Depends(require_permissions("planning:delete")),
    db: Session = Depends(get_db),
):
    planning_service.delete(db, "business-initiatives", entity_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="Business initiative deleted.")


@router.post("/business-initiatives/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_business_initiatives(
    payload: BulkDeleteRequest,
    current_user: CurrentUser = Depends(require_permissions("planning:delete")),
    db: Session = Depends(get_db),
):
    response = planning_service.bulk_delete(db, "business-initiatives", payload.ids, current_user.full_name, current_user.id)
    db.commit()
    return response


@router.get("/overall-assessments", response_model=PaginatedResponse[OverallAssessmentResponse])
def list_overall_assessments(
    query: Annotated[ListQuery, Depends(get_list_query)],
    audit_plan_id: int | None = Query(None),
    _: CurrentUser = Depends(require_permissions("planning:view")),
    db: Session = Depends(get_db),
):
    query.filters = {"audit_plan_id": audit_plan_id} if audit_plan_id else None
    return planning_service.list(db, "overall-assessments", query)


@router.post("/overall-assessments", response_model=OverallAssessmentResponse)
def create_overall_assessment(
    payload: OverallAssessmentCreate,
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    entity = planning_service.create(db, "overall-assessments", payload.model_dump(), current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.put("/overall-assessments/{entity_id}", response_model=OverallAssessmentResponse)
def update_overall_assessment(
    entity_id: int,
    payload: OverallAssessmentUpdate,
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    entity = planning_service.update(db, "overall-assessments", entity_id, payload.model_dump(exclude_none=True), current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.delete("/overall-assessments/{entity_id}", response_model=MessageResponse)
def delete_overall_assessment(
    entity_id: int,
    current_user: CurrentUser = Depends(require_permissions("planning:delete")),
    db: Session = Depends(get_db),
):
    planning_service.delete(db, "overall-assessments", entity_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="Overall assessment deleted.")


@router.post("/overall-assessments/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_overall_assessments(
    payload: BulkDeleteRequest,
    current_user: CurrentUser = Depends(require_permissions("planning:delete")),
    db: Session = Depends(get_db),
):
    response = planning_service.bulk_delete(db, "overall-assessments", payload.ids, current_user.full_name, current_user.id)
    db.commit()
    return response


@router.get("/audit-plans", response_model=PaginatedResponse[AuditPlanResponse])
def list_audit_plans(
    query: Annotated[ListQuery, Depends(get_list_query)],
    company_id: int | None = Query(None),
    location_id: int | None = Query(None),
    quarter: str | None = Query(None),
    _: CurrentUser = Depends(require_permissions("planning:view")),
    db: Session = Depends(get_db),
):
    filters = {}
    if company_id:
        filters["company_id"] = company_id
    if location_id:
        filters["location_id"] = location_id
    if quarter:
        filters["quarter"] = quarter
    query.filters = filters or None
    return audit_service.list_audit_plans(db, query)


@router.post("/audit-plans", response_model=AuditPlanResponse)
def create_audit_plan(
    payload: AuditPlanCreate,
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    entity = audit_service.create_audit_plan(db, payload, current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.put("/audit-plans/{audit_plan_id}", response_model=AuditPlanResponse)
def update_audit_plan(
    audit_plan_id: int,
    payload: AuditPlanUpdate,
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    entity = audit_service.update_audit_plan(db, audit_plan_id, payload, current_user.full_name, current_user.id)
    db.commit()
    return entity


@router.delete("/audit-plans/{audit_plan_id}", response_model=MessageResponse)
def delete_audit_plan(
    audit_plan_id: int,
    current_user: CurrentUser = Depends(require_permissions("planning:delete")),
    db: Session = Depends(get_db),
):
    audit_service.delete_audit_plan(db, audit_plan_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="Audit plan deleted.")


@router.post("/audit-plans/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_audit_plans(
    payload: BulkDeleteRequest,
    current_user: CurrentUser = Depends(require_permissions("planning:delete")),
    db: Session = Depends(get_db),
):
    response = audit_service.bulk_delete_audit_plans(db, payload.ids, current_user.full_name, current_user.id)
    db.commit()
    return response
