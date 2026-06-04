from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ActiveMixin, BaseModel


class Attachment(BaseModel):
    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint("file_size >= 0", name="ck_attachments_file_size_non_negative"),
        Index("ix_attachments_owner_type_owner_id", "owner_type", "owner_id"),
    )

    evidence_code: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    owner_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    uploaded_by: Mapped["User | None"] = relationship("User", back_populates="attachments", foreign_keys=[uploaded_by_user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])


class KnowledgeLibraryItem(ActiveMixin, BaseModel):
    __tablename__ = "knowledge_library_items"

    item_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    approved_for_auditee: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    attachment: Mapped[Attachment | None] = relationship(Attachment)


class ActivityLog(BaseModel):
    __tablename__ = "activity_logs"
    __table_args__ = (
        Index("ix_activity_logs_module_entity_actor_created", "module", "entity_type", "actor_user_id", "created_at"),
    )

    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    actor_user: Mapped["User | None"] = relationship("User", foreign_keys=[actor_user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])


class Notification(BaseModel):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read_due_date", "user_id", "is_read", "due_date"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    user: Mapped["User"] = relationship("User", back_populates="notifications", foreign_keys=[user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
    outbox_entries: Mapped[list["NotificationOutbox"]] = relationship("NotificationOutbox", back_populates="notification", cascade="all, delete-orphan")


class NotificationOutbox(BaseModel):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'dispatched', 'failed')", name="ck_notification_outbox_status_valid"),
        Index("ix_notification_outbox_status_available", "status", "created_at"),
    )

    notification_id: Mapped[int] = mapped_column(ForeignKey("notifications.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="in_app")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    notification: Mapped["Notification"] = relationship("Notification", back_populates="outbox_entries")
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])


class ManagementReview(BaseModel):
    __tablename__ = "management_reviews"
    __table_args__ = (
        CheckConstraint(
            "((audit_id IS NOT NULL AND action_plan_id IS NULL) OR (audit_id IS NULL AND action_plan_id IS NOT NULL))",
            name="ck_management_reviews_exactly_one_target",
        ),
        CheckConstraint(
            "review_decision IN ('Noted', 'Needs Attention', 'Escalated')",
            name="ck_management_reviews_decision_valid",
        ),
        Index("ix_management_reviews_audit_created", "audit_id", "created_at"),
        Index("ix_management_reviews_action_plan_created", "action_plan_id", "created_at"),
    )

    audit_id: Mapped[int | None] = mapped_column(ForeignKey("audits.id"), nullable=True, index=True)
    action_plan_id: Mapped[int | None] = mapped_column(ForeignKey("action_plans.id"), nullable=True, index=True)
    review_note: Mapped[str] = mapped_column(Text, nullable=False)
    review_decision: Mapped[str] = mapped_column(String(50), nullable=False, default="Noted")
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    audit: Mapped["Audit | None"] = relationship("Audit")
    action_plan: Mapped["ActionPlan | None"] = relationship("ActionPlan")
    created_by_user: Mapped["User"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
