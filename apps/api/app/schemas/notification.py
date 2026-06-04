from __future__ import annotations

from datetime import date, datetime

from app.schemas.base import BaseResponse


class NotificationResponse(BaseResponse):
    user_id: int
    title: str
    message: str
    due_date: date | None = None
    is_read: bool
    read_at: datetime | None = None
    sent_at: datetime
