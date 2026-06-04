from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.api.deps.common import get_list_query
from app.db.session import get_db
from app.schemas.action_plan import ActionPlanResponse
from app.schemas.common import ListQuery, PaginatedResponse
from app.schemas.observation import (
    ObservationConvertRequest,
    ObservationCreate,
    ObservationDispositionRequest,
    ObservationIssueRequest,
    ObservationResponse,
    ObservationResponseRequest,
    ObservationUpdate,
)
from app.services.observation import observation_service

router = APIRouter(tags=["observations"])


@router.get("/audits/{audit_id}/observations", response_model=PaginatedResponse[ObservationResponse])
def list_audit_observations(
    audit_id: int,
    query: Annotated[ListQuery, Depends(get_list_query)],
    current_user: CurrentUser = Depends(require_permissions("observations:view")),
    db: Session = Depends(get_db),
):
    return observation_service.list_for_audit(db, audit_id, query, current_user)


@router.post("/audits/{audit_id}/observations", response_model=ObservationResponse)
def create_observation(
    audit_id: int,
    payload: ObservationCreate,
    current_user: CurrentUser = Depends(require_permissions("observations:create")),
    db: Session = Depends(get_db),
):
    entity = observation_service.create(db, audit_id, payload, current_user)
    db.commit()
    return entity


@router.put("/observations/{observation_id}", response_model=ObservationResponse)
def update_observation(
    observation_id: int,
    payload: ObservationUpdate,
    current_user: CurrentUser = Depends(require_permissions("observations:create")),
    db: Session = Depends(get_db),
):
    entity = observation_service.update(db, observation_id, payload, current_user)
    db.commit()
    return entity


@router.post("/observations/{observation_id}/issue", response_model=ObservationResponse)
def issue_observation(
    observation_id: int,
    payload: ObservationIssueRequest,
    current_user: CurrentUser = Depends(require_permissions("observations:issue")),
    db: Session = Depends(get_db),
):
    entity = observation_service.issue(db, observation_id, payload, current_user)
    db.commit()
    return entity


@router.post("/observations/{observation_id}/response", response_model=ObservationResponse)
def respond_to_observation(
    observation_id: int,
    payload: ObservationResponseRequest,
    current_user: CurrentUser = Depends(require_permissions("observations:respond")),
    db: Session = Depends(get_db),
):
    entity = observation_service.respond(db, observation_id, payload, current_user)
    db.commit()
    return entity


@router.post("/observations/{observation_id}/accept", response_model=ObservationResponse)
def accept_observation(
    observation_id: int,
    payload: ObservationDispositionRequest,
    current_user: CurrentUser = Depends(require_permissions("observations:review")),
    db: Session = Depends(get_db),
):
    entity = observation_service.accept(db, observation_id, payload, current_user)
    db.commit()
    return entity


@router.post("/observations/{observation_id}/drop", response_model=ObservationResponse)
def drop_observation(
    observation_id: int,
    payload: ObservationDispositionRequest,
    current_user: CurrentUser = Depends(require_permissions("observations:review")),
    db: Session = Depends(get_db),
):
    entity = observation_service.drop(db, observation_id, payload, current_user)
    db.commit()
    return entity


@router.post("/observations/{observation_id}/convert-to-action-plan", response_model=ActionPlanResponse)
def convert_observation_to_action_plan(
    observation_id: int,
    payload: ObservationConvertRequest,
    current_user: CurrentUser = Depends(require_permissions("observations:convert")),
    db: Session = Depends(get_db),
):
    entity = observation_service.convert_to_action_plan(db, observation_id, payload, current_user)
    db.commit()
    return entity


@router.get("/me/observations", response_model=PaginatedResponse[ObservationResponse])
def my_observations(
    query: Annotated[ListQuery, Depends(get_list_query)],
    current_user: CurrentUser = Depends(require_permissions("observations:view")),
    db: Session = Depends(get_db),
):
    return observation_service.my_observations(db, query, current_user)
