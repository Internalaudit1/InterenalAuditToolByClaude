from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.db.session import get_db
from app.models.support import Notification
from app.schemas.common import MessageResponse
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/notifications", response_model=list[NotificationResponse])
def my_notifications(
    unread: bool | None = Query(None),
    current_user: CurrentUser = Depends(require_permissions("notifications:view")),
    db: Session = Depends(get_db),
):
    stmt = select(Notification).where(Notification.user_id == current_user.id, Notification.is_deleted.is_(False))
    if unread is not None:
        stmt = stmt.where(Notification.is_read.is_(not unread))
    return list(db.scalars(stmt.order_by(desc(Notification.sent_at)).limit(50)).all())


@router.post("/notifications/{notification_id}/read", response_model=MessageResponse)
def mark_notification_read(
    notification_id: int,
    current_user: CurrentUser = Depends(require_permissions("notifications:view")),
    db: Session = Depends(get_db),
):
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
            Notification.is_deleted.is_(False),
        )
    )
    if notification:
        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        notification.updated_by = current_user.full_name
        notification.updated_by_user_id = current_user.id
        db.commit()
    return MessageResponse(message="Notification marked as read.")
