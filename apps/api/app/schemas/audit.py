from __future__ import annotations

from datetime import date

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
    remarks: str | None = None


class AuditPlanResponse(BaseResponse, AuditPlanFields):
    audit_number: str
    period_type: str | None = None
    period_value: str | None = None
    quarter: str


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
    remarks: str | None = None
    history_timeline: list[dict] | None = None


class AuditResponse(BaseResponse, AuditFields):
    audit_number: str
    history_timeline: list[dict] | None = None
