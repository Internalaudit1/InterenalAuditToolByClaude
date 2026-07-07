from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.audit import AuditResponse
from app.schemas.base import BaseResponse


class AuditAllocationFields(BaseModel):
    lead_auditor_user_id: int
    junior_auditor_1_id: int | None = None
    junior_auditor_2_id: int | None = None
    mentor_user_id: int | None = None
    auditee_spoc_user_id: int | None = None
    auditee_spoc_auditee_id: int | None = None
    period_type: str | None = None
    period_value: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    remarks: str | None = None


class AuditAllocationCreate(AuditAllocationFields):
    model_config = ConfigDict(extra="forbid")

    audit_plan_id: int


class AuditAllocationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_auditor_user_id: int | None = None
    junior_auditor_1_id: int | None = None
    junior_auditor_2_id: int | None = None
    mentor_user_id: int | None = None
    auditee_spoc_user_id: int | None = None
    auditee_spoc_auditee_id: int | None = None
    period_type: str | None = None
    period_value: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    remarks: str | None = None


class AuditAllocationResponse(BaseResponse, AuditAllocationFields):
    audit_plan_id: int
    allocation_code: str
    status: str = "Draft"
    audit_id: int | None = None
    approved_by_user_id: int | None = None
    approved_at: datetime | None = None
    audit_plan_number: str | None = None
    audit_plan_name: str | None = None
    lead_auditor_name: str | None = None
    junior_auditor_1_name: str | None = None
    junior_auditor_2_name: str | None = None
    mentor_name: str | None = None


class AllocatablePlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    audit_number: str
    audit_name: str
    audit_area: str | None = None
    company_id: int
    location_id: int
    fiscal_year: str
    criticality: str | None = None
    caro_status: str | None = None
    audit_scope_type: str | None = None


class AuditAllocationInitiateResponse(AuditResponse):
    pass
