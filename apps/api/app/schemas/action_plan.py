from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.base import BaseResponse


class ActionPlanFields(BaseModel):
    audit_id: int
    observation_id: int | None = None
    location_id: int
    root_cause_id: int | None = None
    observation_heading: str
    observation_grading_id: int
    detailed_observation: str | None = None
    risk_type_id: int
    agreed_timeline: date
    review_quarter: str | None = None
    responsibility_department: str | None = None
    implementation_owner_user_id: int
    assigned_auditor_user_id: int
    auditor_implementation_remarks: str | None = None
    management_response: str | None = None
    agreed_action_plan: str | None = None


class ActionPlanCreate(ActionPlanFields):
    model_config = ConfigDict(extra="forbid")

    auditor_status: str
    auditee_status: str
    revised_date: date | None = None
    revision_count: int = 0


class ActionPlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_cause_id: int | None = None
    observation_heading: str | None = None
    observation_grading_id: int | None = None
    detailed_observation: str | None = None
    risk_type_id: int | None = None
    agreed_timeline: date | None = None
    review_quarter: str | None = None
    responsibility_department: str | None = None
    implementation_owner_user_id: int | None = None
    assigned_auditor_user_id: int | None = None
    auditor_implementation_remarks: str | None = None


class ActionPlanResponseRequest(BaseModel):
    management_response: str
    agreed_action_plan: str
    management_implementation_remarks: str
    auditee_status: str
    revised_date: date | None = None
    attachment_ids: list[int] = []


class ActionPlanRemarksRequest(BaseModel):
    management_implementation_remarks: str


class ActionPlanReviewRequest(BaseModel):
    auditor_status: str
    auditor_implementation_remarks: str


class ActionPlanReopenRequest(BaseModel):
    auditor_implementation_remarks: str
    revised_date: date | None = None
    reason: str


class ActionPlanRevisionResponse(BaseResponse):
    action_plan_id: int
    response_code: str | None = None
    revision_number: int
    management_implementation_remarks: str | None = None
    revised_date: date | None = None
    file_attachment_id: int | None = None
    updated_by_user_id: int | None = None
    status_snapshot: dict | None = None


class ActionPlanResponse(BaseResponse, ActionPlanFields):
    action_plan_id: str
    audit_number: str
    observation_number: str | None = None
    auditor_status: str
    auditee_status: str
    revised_date: date | None = None
    revision_count: int
    management_implementation_remarks: str | None = None
    completed_at: datetime | None = None
    last_response_at: datetime | None = None
    last_review_at: datetime | None = None
    metadata_json: dict | None = None
    revisions: list[ActionPlanRevisionResponse] = []
