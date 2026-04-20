from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.schemas.base import BaseResponse


class ProcessRiskMappingBase(BaseModel):
    audit_plan_id: int
    process_location_mapping_id: int | None = None
    trial_balance_id: int | None = None
    quantitative_assessment: str | None = None
    qualitative_assessment: str | None = None
    final_process_rating: str | None = None


class ProcessRiskMappingCreate(ProcessRiskMappingBase):
    pass


class ProcessRiskMappingUpdate(BaseModel):
    process_location_mapping_id: int | None = None
    trial_balance_id: int | None = None
    quantitative_assessment: str | None = None
    qualitative_assessment: str | None = None
    final_process_rating: str | None = None


class ProcessRiskMappingResponse(BaseResponse, ProcessRiskMappingBase):
    pass


class ERMRiskBase(BaseModel):
    audit_plan_id: int
    erm_risk_code: str
    erm_risk_title: str
    description: str | None = None
    rating: str | None = None
    process_id: int | None = None


class ERMRiskCreate(ERMRiskBase):
    pass


class ERMRiskUpdate(BaseModel):
    erm_risk_code: str | None = None
    erm_risk_title: str | None = None
    description: str | None = None
    rating: str | None = None
    process_id: int | None = None


class ERMRiskResponse(BaseResponse, ERMRiskBase):
    pass


class BusinessInitiativeBase(BaseModel):
    audit_plan_id: int
    initiative_code: str
    title: str
    description: str | None = None
    impact: str | None = None
    owner_user_id: int | None = None
    timeline: str | None = None


class BusinessInitiativeCreate(BusinessInitiativeBase):
    pass


class BusinessInitiativeUpdate(BaseModel):
    initiative_code: str | None = None
    title: str | None = None
    description: str | None = None
    impact: str | None = None
    owner_user_id: int | None = None
    timeline: str | None = None


class BusinessInitiativeResponse(BaseResponse, BusinessInitiativeBase):
    pass


class OverallAssessmentBase(BaseModel):
    audit_plan_id: int
    location_id: int
    overall_risk: str
    coverage_status: str
    justification: str | None = None
    last_audited_date: date | None = None


class OverallAssessmentCreate(OverallAssessmentBase):
    pass


class OverallAssessmentUpdate(BaseModel):
    location_id: int | None = None
    overall_risk: str | None = None
    coverage_status: str | None = None
    justification: str | None = None
    last_audited_date: date | None = None


class OverallAssessmentResponse(BaseResponse, OverallAssessmentBase):
    pass

