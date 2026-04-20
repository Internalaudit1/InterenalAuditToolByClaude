from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.support import ActivityLog, Notification


class ActivityLogService:
    def log(
        self,
        db: Session,
        *,
        actor_user_id: int | None,
        actor_name: str | None,
        role: str | None,
        module: str,
        entity_type: str,
        entity_id: str,
        action_type: str,
        old_values: dict | None = None,
        new_values: dict | None = None,
        request_path: str | None = None,
        request_method: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
    ) -> ActivityLog:
        log = ActivityLog(
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            role=role,
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=action_type,
            old_values=old_values,
            new_values=new_values,
            request_path=request_path,
            request_method=request_method,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            created_by=actor_name,
            updated_by=actor_name,
        )
        db.add(log)
        db.flush()
        db.refresh(log)
        return log

    def notify(self, db: Session, *, user_id: int, title: str, message: str) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            created_by="system",
            updated_by="system",
        )
        db.add(notification)
        db.flush()
        db.refresh(notification)
        return notification


activity_log_service = ActivityLogService()

