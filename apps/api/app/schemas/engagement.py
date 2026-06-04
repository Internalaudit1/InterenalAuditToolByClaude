from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import EngagementDocumentType, EngagementPlanStatus, EngagementResourceRole
from app.schemas.base import BaseResponse


class EngagementPlanFields(BaseModel):
    audit_id: int
    title: str
    objective: str | None = None
    scope: str | None = None
    scope_exclusions: str | None = None
    audit_period_from: date | None = None
    audit_period_to: date | None = None
    kickoff_date: date | None = None
    planned_start_date: date
    planned_end_date: date
    lead_auditor_id: int | None = None
    reviewer_id: int | None = None
    auditee_spoc_auditee_id: int | None = None
    auditee_spoc_id: int | None = None
    planned_hours: float | None = None
    approved_hours: float | None = None


class EngagementPlanCreate(EngagementPlanFields):
    model_config = ConfigDict(extra="forbid")


class EngagementPlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    objective: str | None = None
    scope: str | None = None
    scope_exclusions: str | None = None
    audit_period_from: date | None = None
    audit_period_to: date | None = None
    kickoff_date: date | None = None
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    lead_auditor_id: int | None = None
    reviewer_id: int | None = None
    auditee_spoc_auditee_id: int | None = None
    auditee_spoc_id: int | None = None
    planned_hours: float | None = None
    approved_hours: float | None = None


class EngagementDecisionRequest(BaseModel):
    remarks: str | None = None


class EngagementPlanResponse(BaseResponse):
    engagement_code: str
    audit_id: int
    company_id: int
    location_id: int
    title: str
    objective: str | None = None
    scope: str | None = None
    scope_exclusions: str | None = None
    audit_period_from: date | None = None
    audit_period_to: date | None = None
    kickoff_date: date | None = None
    planned_start_date: date
    planned_end_date: date
    status: EngagementPlanStatus
    lead_auditor_id: int | None = None
    reviewer_id: int | None = None
    auditee_spoc_auditee_id: int | None = None
    auditee_spoc_id: int | None = None
    lead_auditor_name: str | None = None
    reviewer_name: str | None = None
    auditee_spoc_name: str | None = None
    planned_hours: float | None = None
    approved_hours: float | None = None


class EngagementPlanPrefillResponse(EngagementPlanFields):
    audit_number: str
    audit_name: str
    company_id: int
    location_id: int
    lead_auditor_name: str | None = None
    reviewer_name: str | None = None
    auditee_spoc_name: str | None = None
    can_create: bool = True
    existing_engagement_plan_id: int | None = None


class KickoffChecklistItemPatch(BaseModel):
    id: int | None = None
    check_item: str
    is_mandatory: bool = True
    is_completed: bool = False
    remarks: str | None = None


class KickoffChecklistPatchRequest(BaseModel):
    items: list[KickoffChecklistItemPatch]


class KickoffChecklistItemResponse(BaseResponse):
    engagement_plan_id: int
    check_item: str
    is_mandatory: bool
    is_completed: bool
    completed_by_user_id: int | None = None
    completed_at: datetime | None = None
    remarks: str | None = None


class EngagementResourceCreate(BaseModel):
    user_id: int
    role_in_engagement: EngagementResourceRole
    planned_hours: float | None = None
    approved_hours: float | None = None
    actual_hours: float | None = None


class EngagementResourceUpdate(BaseModel):
    role_in_engagement: EngagementResourceRole | None = None
    planned_hours: float | None = None
    approved_hours: float | None = None
    actual_hours: float | None = None


class EngagementResourceResponse(BaseResponse):
    engagement_plan_id: int
    user_id: int
    role_in_engagement: EngagementResourceRole
    user_name: str | None = None
    planned_hours: float | None = None
    approved_hours: float | None = None
    actual_hours: float | None = None


class EngagementDocumentResponse(BaseResponse):
    engagement_plan_id: int
    document_type: EngagementDocumentType
    document_id: int
    is_latest: bool
