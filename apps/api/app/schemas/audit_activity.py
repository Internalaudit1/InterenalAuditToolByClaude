from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.schemas.base import BaseResponse


class AuditActivityFields(BaseModel):
    title: str
    objective: str | None = None
    description: str | None = None
    assigned_to_user_id: int | None = None
    due_date: date | None = None
    status: str = "Yet to Start"
    remarks: str | None = None


class AuditActivityCreate(AuditActivityFields):
    model_config = ConfigDict(extra="forbid")


class AuditActivityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    objective: str | None = None
    description: str | None = None
    assigned_to_user_id: int | None = None
    due_date: date | None = None
    status: str | None = None
    remarks: str | None = None


class AuditActivityAssignRequest(BaseModel):
    assigned_to_user_id: int | None = None


class AuditActivityStatusRequest(BaseModel):
    status: str
    remarks: str | None = None


class AuditActivityResponse(BaseResponse, AuditActivityFields):
    audit_id: int
    assigned_to_name: str | None = None
