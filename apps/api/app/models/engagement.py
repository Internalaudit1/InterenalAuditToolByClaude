from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class EngagementPlan(BaseModel):
    __tablename__ = "engagement_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Draft', 'Submitted', 'Approved', 'Rejected', 'Kicked Off')",
            name="ck_engagement_plans_status_valid",
        ),
        CheckConstraint("planned_end_date >= planned_start_date", name="ck_engagement_plans_date_range"),
        Index("ix_engagement_plans_audit_status", "audit_id", "status"),
        Index("ix_engagement_plans_company_location", "company_id", "location_id"),
    )

    engagement_code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_exclusions: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_period_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    audit_period_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    kickoff_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Draft")
    lead_auditor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    auditee_spoc_auditee_id: Mapped[int | None] = mapped_column(ForeignKey("auditees.id"), nullable=True)
    auditee_spoc_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    planned_hours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    approved_hours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    audit: Mapped["Audit"] = relationship("Audit", back_populates="engagement_plans")
    company: Mapped["Company"] = relationship("Company")
    location: Mapped["Location"] = relationship("Location")
    lead_auditor: Mapped["User | None"] = relationship("User", foreign_keys=[lead_auditor_id])
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewer_id])
    auditee_spoc_auditee: Mapped["Auditee | None"] = relationship("Auditee", foreign_keys=[auditee_spoc_auditee_id])
    auditee_spoc: Mapped["User | None"] = relationship("User", foreign_keys=[auditee_spoc_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
    kickoff_checklist_items: Mapped[list["EngagementKickoffChecklist"]] = relationship(
        "EngagementKickoffChecklist",
        back_populates="engagement_plan",
        cascade="all, delete-orphan",
    )
    resources: Mapped[list["EngagementResource"]] = relationship(
        "EngagementResource",
        back_populates="engagement_plan",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list["EngagementDocument"]] = relationship(
        "EngagementDocument",
        back_populates="engagement_plan",
        cascade="all, delete-orphan",
    )

    @property
    def lead_auditor_name(self) -> str | None:
        return self.lead_auditor.full_name if self.lead_auditor else None

    @property
    def reviewer_name(self) -> str | None:
        return self.reviewer.full_name if self.reviewer else None

    @property
    def auditee_spoc_name(self) -> str | None:
        if self.auditee_spoc_auditee:
            return self.auditee_spoc_auditee.full_name
        return self.auditee_spoc.full_name if self.auditee_spoc else None


class EngagementKickoffChecklist(BaseModel):
    __tablename__ = "engagement_kickoff_checklists"
    __table_args__ = (
        Index("ix_engagement_kickoff_checklists_plan_completed", "engagement_plan_id", "is_completed"),
    )

    engagement_plan_id: Mapped[int] = mapped_column(ForeignKey("engagement_plans.id"), nullable=False, index=True)
    check_item: Mapped[str] = mapped_column(String(255), nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    engagement_plan: Mapped["EngagementPlan"] = relationship("EngagementPlan", back_populates="kickoff_checklist_items")
    completed_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[completed_by_user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])


class EngagementResource(BaseModel):
    __tablename__ = "engagement_resources"
    __table_args__ = (
        CheckConstraint(
            "role_in_engagement IN ('Lead Auditor', 'Reviewer', 'Junior Auditor', 'Audit Support', 'Auditee SPOC', 'Observer')",
            name="ck_engagement_resources_role_valid",
        ),
        Index("ix_engagement_resources_plan_user", "engagement_plan_id", "user_id"),
    )

    engagement_plan_id: Mapped[int] = mapped_column(ForeignKey("engagement_plans.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role_in_engagement: Mapped[str] = mapped_column(String(100), nullable=False)
    planned_hours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    approved_hours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    actual_hours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    engagement_plan: Mapped["EngagementPlan"] = relationship("EngagementPlan", back_populates="resources")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])

    @property
    def user_name(self) -> str | None:
        return self.user.full_name if self.user else None


class EngagementDocument(BaseModel):
    __tablename__ = "engagement_documents"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('Engagement Letter', 'Scope Memo', 'Kickoff Minutes', 'Resource Plan', 'Budget Workbook', 'Other')",
            name="ck_engagement_documents_type_valid",
        ),
        Index("ix_engagement_documents_plan_type_latest", "engagement_plan_id", "document_type", "is_latest"),
    )

    engagement_plan_id: Mapped[int] = mapped_column(ForeignKey("engagement_plans.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"), nullable=False, index=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    engagement_plan: Mapped["EngagementPlan"] = relationship("EngagementPlan", back_populates="documents")
    document: Mapped["Attachment"] = relationship("Attachment")
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
