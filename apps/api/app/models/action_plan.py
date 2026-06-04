from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ActionPlan(BaseModel):
    __tablename__ = "action_plans"
    __table_args__ = (
        CheckConstraint(
            "auditor_status IN ('Pending to be initiated', 'In Progress', 'Under Review', 'Completed', 'Reopened')",
            name="ck_action_plans_auditor_status_valid",
        ),
        CheckConstraint(
            "auditee_status IN ('Pending to be initiated', 'In Progress', 'Under Review', 'Completed', 'Reopened')",
            name="ck_action_plans_auditee_status_valid",
        ),
        CheckConstraint("revision_count >= 0", name="ck_action_plans_revision_count_non_negative"),
        Index("ix_action_plans_audit_location_status", "audit_id", "location_id", "auditor_status", "auditee_status"),
        Index("ix_action_plans_timeline_and_assignments", "agreed_timeline", "observation_grading_id", "implementation_owner_user_id", "assigned_auditor_user_id"),
    )

    action_plan_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False)
    observation_id: Mapped[int | None] = mapped_column(ForeignKey("observations.id"), nullable=True, index=True)
    audit_number: Mapped[str] = mapped_column(String(100), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    root_cause_id: Mapped[int | None] = mapped_column(ForeignKey("root_causes.id"), nullable=True)
    observation_heading: Mapped[str] = mapped_column(String(255), nullable=False)
    observation_grading_id: Mapped[int] = mapped_column(ForeignKey("observation_gradings.id"), nullable=False)
    detailed_observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_type_id: Mapped[int] = mapped_column(ForeignKey("risk_types.id"), nullable=False)
    agreed_timeline: Mapped[date] = mapped_column(Date, nullable=False)
    auditor_status: Mapped[str] = mapped_column(String(50), nullable=False)
    auditee_status: Mapped[str] = mapped_column(String(50), nullable=False)
    review_quarter: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observation_number: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    responsibility_department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auditor_implementation_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    management_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    agreed_action_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    implementation_owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_auditor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    revised_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    revision_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    management_implementation_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    audit: Mapped["Audit"] = relationship("Audit", back_populates="action_plans")
    observation: Mapped["Observation | None"] = relationship("Observation", back_populates="action_plans")
    location: Mapped["Location"] = relationship("Location")
    root_cause: Mapped["RootCause | None"] = relationship("RootCause")
    observation_grading: Mapped["ObservationGrading"] = relationship("ObservationGrading")
    risk_type: Mapped["RiskType"] = relationship("RiskType")
    implementation_owner: Mapped["User"] = relationship("User", foreign_keys=[implementation_owner_user_id])
    assigned_auditor: Mapped["User"] = relationship("User", foreign_keys=[assigned_auditor_user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
    revisions: Mapped[list["ActionPlanRevision"]] = relationship(
        "ActionPlanRevision",
        back_populates="action_plan",
        cascade="all, delete-orphan",
    )


class ActionPlanRevision(BaseModel):
    __tablename__ = "action_plan_revisions"

    action_plan_id: Mapped[int] = mapped_column(ForeignKey("action_plans.id"), nullable=False, index=True)
    response_code: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    management_implementation_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    revised_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_action_plan_revisions_action_plan_revised_date", "action_plan_id", "revised_date"),
    )

    action_plan: Mapped[ActionPlan] = relationship(ActionPlan, back_populates="revisions")
    file_attachment: Mapped["Attachment | None"] = relationship("Attachment")
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
