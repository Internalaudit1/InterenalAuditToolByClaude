from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import AuditEventType
from app.models.audit import Audit, AuditEvent
from app.repositories.base import BaseRepository
from app.utils.serialization import model_to_dict


class AuditEventService:
    repo = BaseRepository(AuditEvent)

    def record(
        self,
        db: Session,
        *,
        audit: Audit,
        event_type: AuditEventType | str,
        event_title: str,
        actor_name: str | None,
        actor_id: int | None,
        description: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        payload: dict | None = None,
    ) -> AuditEvent:
        data = {
            "audit_id": audit.id,
            "company_id": audit.company_id,
            "location_id": audit.location_id,
            "event_type": event_type.value if isinstance(event_type, AuditEventType) else event_type,
            "event_title": event_title,
            "description": description,
            "from_status": from_status,
            "to_status": to_status,
            "payload": payload,
            "created_by": actor_name,
            "updated_by": actor_name,
            "created_by_user_id": actor_id,
            "updated_by_user_id": actor_id,
        }
        return self.repo.create(db, data)

    def summarize(self, event: AuditEvent) -> dict:
        return model_to_dict(event)


audit_event_service = AuditEventService()
