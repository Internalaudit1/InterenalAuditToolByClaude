from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.base import BaseResponse


class ObservationFields(BaseModel):
    activity_id: int | None = None
    heading: str | None = None
    background: str | None = None
    observation_text: str | None = None
    risk_implication: str | None = None
    recommendation: str | None = None
    root_cause_id: int | None = None
    observation_grading_id: int
    risk_type_id: int
    auditee_id: int | None = None
    auditee_user_id: int | None = None


class ObservationCreate(ObservationFields):
    model_config = ConfigDict(extra="forbid")

    heading: str
    observation_text: str


class ObservationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: int | None = None
    heading: str | None = None
    background: str | None = None
    observation_text: str | None = None
    risk_implication: str | None = None
    recommendation: str | None = None
    root_cause_id: int | None = None
    observation_grading_id: int | None = None
    risk_type_id: int | None = None
    auditee_id: int | None = None
    auditee_user_id: int | None = None


class ObservationIssueRequest(BaseModel):
    auditee_id: int | None = None
    auditee_user_id: int | None = None


class ObservationResponseRequest(BaseModel):
    auditee_remark: str


class ObservationDispositionRequest(BaseModel):
    remarks: str | None = None


class ObservationConvertRequest(BaseModel):
    agreed_timeline: date
    implementation_owner_user_id: int | None = None
    assigned_auditor_user_id: int | None = None
    responsibility_department: str | None = None
    agreed_action_plan: str | None = None


class ObservationResponse(BaseResponse, ObservationFields):
    observation_number: str
    audit_id: int
    status: str
    auditee_name: str | None = None
    auditee_code: str | None = None
    auditee_remark: str | None = None
    issued_at: datetime | None = None
    responded_at: datetime | None = None
