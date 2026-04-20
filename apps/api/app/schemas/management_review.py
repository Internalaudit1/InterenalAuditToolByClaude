from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class ManagementReviewCreate(BaseModel):
    review_note: str = Field(min_length=3, max_length=4000)
    review_decision: str = Field(default="Noted", pattern="^(Noted|Needs Attention|Escalated)$")


class ManagementReviewResponse(BaseResponse):
    audit_id: int | None = None
    action_plan_id: int | None = None
    review_note: str
    review_decision: str
    created_by_user_id: int
    created_by_user_name: str | None = None
