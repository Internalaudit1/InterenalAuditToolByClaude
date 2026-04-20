from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AuditFieldsMixin(BaseModel):
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None


class BaseResponse(ORMModel, AuditFieldsMixin):
    id: int
    is_deleted: bool = False


class DateRange(BaseModel):
    start_date: date | None = None
    end_date: date | None = None

