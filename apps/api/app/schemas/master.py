from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.schemas.base import BaseResponse


class MasterRecordBase(BaseModel):
    code: str | None = None
    name: str | None = None
    title: str | None = None
    description: str | None = None
    country_id: int | None = None
    state_id: int | None = None
    city_id: int | None = None
    company_id: int | None = None
    process_id: int | None = None
    location_id: int | None = None
    trial_balance_id: int | None = None
    audit_name: str | None = None
    sector: str | None = None
    business_cycle: str | None = None
    pan: str | None = None
    gst_no: str | None = None
    division_id: str | None = None
    division_description: str | None = None
    profit_center_code: str | None = None
    location_code: str | None = None
    risk_index: str | None = None
    severity_rank: int | None = None
    escalation_days: int | None = None
    threshold: str | None = None
    source_designation_id: int | None = None
    target_designation_id: int | None = None
    max_tasks: int | None = None
    approver_config: list[dict[str, Any]] | None = None
    amount: Decimal | None = None
    is_active: bool | None = None


class MasterRecordCreate(MasterRecordBase):
    pass


class MasterRecordUpdate(MasterRecordBase):
    pass


class MasterRecordResponse(BaseResponse, MasterRecordBase):
    pass
