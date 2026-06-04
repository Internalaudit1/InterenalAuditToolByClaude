from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.base import BaseResponse


class AuditPlanFields(BaseModel):
    audit_name: str
    company_id: int
    location_id: int
    period_type: str
    period_value: str
    fiscal_year: str
    start_date: date
    end_date: date
    planned_flag: bool = True
    criticality: str
    audit_owner_id: int | None = None
    junior_auditor_1_id: int | None = None
    junior_auditor_2_id: int | None = None
    remarks: str | None = None


class AuditPlanCreate(AuditPlanFields):
    model_config = ConfigDict(extra="forbid")


class AuditPlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_name: str | None = None
    company_id: int | None = None
    location_id: int | None = None
    period_type: str | None = None
    period_value: str | None = None
    fiscal_year: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    planned_flag: bool | None = None
    criticality: str | None = None
    audit_owner_id: int | None = None
    junior_auditor_1_id: int | None = None
    junior_auditor_2_id: int | None = None
    remarks: str | None = None


class AuditPlanResponse(BaseResponse, AuditPlanFields):
    audit_number: str
    period_type: str | None = None
    period_value: str | None = None
    quarter: str
    audit_owner_name: str | None = None
    junior_auditor_1_name: str | None = None
    junior_auditor_2_name: str | None = None
    approval_status: str = "Draft"
    approved_by_user_id: int | None = None
    approved_at: datetime | None = None


class AuditFields(BaseModel):
    audit_name: str
    company_id: int
    location_id: int
    quarter: str
    period_type: str | None = None
    period_value: str | None = None
    fiscal_year: str
    start_date: date
    end_date: date
    planned_flag: bool = True
    criticality: str
    audit_owner_id: int | None = None
    reviewer_user_id: int | None = None
    auditee_spoc_auditee_id: int | None = None
    auditee_spoc_user_id: int | None = None
    remarks: str | None = None
    audit_plan_id: int | None = None
    status: str


class AuditCreate(AuditFields):
    model_config = ConfigDict(extra="forbid")

    history_timeline: list[dict] | None = None


class AuditUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_name: str | None = None
    company_id: int | None = None
    location_id: int | None = None
    quarter: str | None = None
    period_type: str | None = None
    period_value: str | None = None
    fiscal_year: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    planned_flag: bool | None = None
    criticality: str | None = None
    audit_owner_id: int | None = None
    reviewer_user_id: int | None = None
    auditee_spoc_auditee_id: int | None = None
    auditee_spoc_user_id: int | None = None
    remarks: str | None = None
    history_timeline: list[dict] | None = None


class AuditResponse(BaseResponse, AuditFields):
    audit_number: str
    audit_owner_name: str | None = None
    reviewer_name: str | None = None
    auditee_spoc_name: str | None = None
    history_timeline: list[dict] | None = None
    assignment_history: list[dict] | None = None
    events: list["AuditEventResponse"] | None = None


class AuditEventResponse(BaseResponse):
    audit_id: int
    company_id: int | None = None
    location_id: int | None = None
    event_type: str
    event_title: str
    description: str | None = None
    from_status: str | None = None
    to_status: str | None = None
    payload: dict | None = None


class AuditPlanInitiateRequest(BaseModel):
    reviewer_user_id: int | None = None
    auditee_spoc_auditee_id: int | None = None
    auditee_spoc_user_id: int | None = None


class AuditMembershipCreate(BaseModel):
    user_id: int
    role_on_audit: str


class AuditMembershipResponse(BaseResponse):
    audit_id: int
    user_id: int
    role_on_audit: str
    user_name: str | None = None


class AuditCompletionResponse(BaseModel):
    completed: int
    total: int
    percentage: float
