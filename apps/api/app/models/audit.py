from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AuditPlan(BaseModel):
    __tablename__ = "audit_plans"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_audit_plans_date_range"),
        CheckConstraint(
            "approval_status IN ('Draft', 'Under Review', 'Approved', 'Deferred', 'Cancelled')",
            name="ck_audit_plans_approval_status_valid",
        ),
        Index("ix_audit_plans_company_location_quarter", "company_id", "location_id", "quarter"),
        Index("ix_audit_plans_fiscal_year_planned_flag", "fiscal_year", "planned_flag"),
    )

    audit_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    audit_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    period_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    period_value: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fiscal_year: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_flag: Mapped[bool] = mapped_column(default=True, nullable=False)
    criticality: Mapped[str] = mapped_column(String(50), nullable=False)
    audit_owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    junior_auditor_1_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    junior_auditor_2_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_status: Mapped[str] = mapped_column(String(50), default="Draft", nullable=False)
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship("Company")
    location: Mapped["Location"] = relationship("Location")
    audit_owner: Mapped["User | None"] = relationship("User", foreign_keys=[audit_owner_id])
    junior_auditor_1: Mapped["User | None"] = relationship("User", foreign_keys=[junior_auditor_1_id])
    junior_auditor_2: Mapped["User | None"] = relationship("User", foreign_keys=[junior_auditor_2_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
    approved_by: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by_user_id])
    audit: Mapped["Audit | None"] = relationship("Audit", back_populates="audit_plan", uselist=False)
    process_risk_mappings: Mapped[list["ProcessRiskMapping"]] = relationship(
        "ProcessRiskMapping",
        back_populates="audit_plan",
        cascade="all, delete-orphan",
    )
    erm_risks: Mapped[list["ERMRisk"]] = relationship("ERMRisk", back_populates="audit_plan", cascade="all, delete-orphan")
    business_initiatives: Mapped[list["BusinessInitiative"]] = relationship(
        "BusinessInitiative",
        back_populates="audit_plan",
        cascade="all, delete-orphan",
    )
    overall_assessments: Mapped[list["OverallAssessment"]] = relationship(
        "OverallAssessment",
        back_populates="audit_plan",
        cascade="all, delete-orphan",
    )

    @property
    def audit_owner_name(self) -> str | None:
        return self.audit_owner.full_name if self.audit_owner else None

    @property
    def junior_auditor_1_name(self) -> str | None:
        return self.junior_auditor_1.full_name if self.junior_auditor_1 else None

    @property
    def junior_auditor_2_name(self) -> str | None:
        return self.junior_auditor_2.full_name if self.junior_auditor_2 else None


class Audit(BaseModel):
    __tablename__ = "audits"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_audits_date_range"),
        CheckConstraint(
            "status IN ('To be Initiated', 'In Progress', 'Completed', 'Overdue', 'Unplanned')",
            name="ck_audits_status_valid",
        ),
        Index("ix_audits_status_company_location", "status", "company_id", "location_id"),
        Index("ix_audits_quarter_planned_flag_end_date", "quarter", "planned_flag", "end_date"),
    )

    audit_plan_id: Mapped[int | None] = mapped_column(ForeignKey("audit_plans.id"), nullable=True)
    audit_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    audit_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    period_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    period_value: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fiscal_year: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    planned_flag: Mapped[bool] = mapped_column(default=True, nullable=False)
    criticality: Mapped[str] = mapped_column(String(50), nullable=False)
    audit_owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    auditee_spoc_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    auditee_spoc_auditee_id: Mapped[int | None] = mapped_column(ForeignKey("auditees.id"), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    history_timeline: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    assignment_history: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)

    audit_plan: Mapped[AuditPlan | None] = relationship(AuditPlan, back_populates="audit")
    company: Mapped["Company"] = relationship("Company")
    location: Mapped["Location"] = relationship("Location")
    audit_owner: Mapped["User | None"] = relationship("User", foreign_keys=[audit_owner_id])
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewer_user_id])
    auditee_spoc: Mapped["User | None"] = relationship("User", foreign_keys=[auditee_spoc_user_id])
    auditee_spoc_auditee: Mapped["Auditee | None"] = relationship("Auditee", foreign_keys=[auditee_spoc_auditee_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
    action_plans: Mapped[list["ActionPlan"]] = relationship("ActionPlan", back_populates="audit")
    memberships: Mapped[list["AuditMembership"]] = relationship("AuditMembership", back_populates="audit", cascade="all, delete-orphan")
    activities: Mapped[list["AuditActivity"]] = relationship("AuditActivity", back_populates="audit", cascade="all, delete-orphan")
    observations: Mapped[list["Observation"]] = relationship("Observation", back_populates="audit", cascade="all, delete-orphan")
    events: Mapped[list["AuditEvent"]] = relationship("AuditEvent", back_populates="audit", cascade="all, delete-orphan")
    engagement_plans: Mapped[list["EngagementPlan"]] = relationship("EngagementPlan", back_populates="audit", cascade="all, delete-orphan")

    @property
    def audit_owner_name(self) -> str | None:
        return self.audit_owner.full_name if self.audit_owner else None

    @property
    def reviewer_name(self) -> str | None:
        return self.reviewer.full_name if self.reviewer else None

    @property
    def auditee_spoc_name(self) -> str | None:
        if self.auditee_spoc_auditee:
            return self.auditee_spoc_auditee.full_name
        return self.auditee_spoc.full_name if self.auditee_spoc else None


class AuditEvent(BaseModel):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_audit_created", "audit_id", "created_at"),
        Index("ix_audit_events_company_location", "company_id", "location_id"),
    )

    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    audit: Mapped["Audit"] = relationship("Audit", back_populates="events")
    company: Mapped["Company | None"] = relationship("Company")
    location: Mapped["Location | None"] = relationship("Location")
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])


class AuditMembership(BaseModel):
    __tablename__ = "audit_memberships"
    __table_args__ = (
        CheckConstraint(
            "role_on_audit IN ('lead_auditor', 'junior_auditor', 'reviewer', 'auditee_spoc', 'observer')",
            name="ck_audit_memberships_role_valid",
        ),
        UniqueConstraint("audit_id", "user_id", "role_on_audit", name="uq_audit_memberships_audit_user_role"),
        Index("ix_audit_memberships_audit_user", "audit_id", "user_id"),
        Index("ix_audit_memberships_user_role", "user_id", "role_on_audit"),
    )

    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_on_audit: Mapped[str] = mapped_column(String(50), nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    audit: Mapped["Audit"] = relationship("Audit", back_populates="memberships")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])

    @property
    def user_name(self) -> str | None:
        return self.user.full_name if self.user else None


class AuditActivity(BaseModel):
    __tablename__ = "audit_activities"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Yet to Start', 'Work in Progress', 'Completed', 'Not Applicable')",
            name="ck_audit_activities_status_valid",
        ),
        Index("ix_audit_activities_audit_assignee_status", "audit_id", "assigned_to_user_id", "status"),
        Index("ix_audit_activities_due_date", "due_date"),
    )

    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Yet to Start", nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    audit: Mapped["Audit"] = relationship("Audit", back_populates="activities")
    assigned_to: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])

    @property
    def assigned_to_name(self) -> str | None:
        return self.assigned_to.full_name if self.assigned_to else None


class Observation(BaseModel):
    __tablename__ = "observations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Draft', 'Issued', 'Responded', 'Accepted', 'Converted', 'Dropped')",
            name="ck_observations_status_valid",
        ),
        Index("ix_observations_audit_status", "audit_id", "status"),
        Index("ix_observations_activity_status", "activity_id", "status"),
        Index("ix_observations_auditee_status", "auditee_user_id", "status"),
    )

    observation_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("audit_activities.id"), nullable=True)
    heading: Mapped[str] = mapped_column(String(255), nullable=False)
    background: Mapped[str | None] = mapped_column(Text, nullable=True)
    observation_text: Mapped[str] = mapped_column(Text, nullable=False)
    risk_implication: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_id: Mapped[int | None] = mapped_column(ForeignKey("root_causes.id"), nullable=True)
    observation_grading_id: Mapped[int] = mapped_column(ForeignKey("observation_gradings.id"), nullable=False)
    risk_type_id: Mapped[int] = mapped_column(ForeignKey("risk_types.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Draft", nullable=False)
    auditee_id: Mapped[int | None] = mapped_column(ForeignKey("auditees.id"), nullable=True)
    auditee_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    auditee_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    audit: Mapped["Audit"] = relationship("Audit", back_populates="observations")
    activity: Mapped["AuditActivity | None"] = relationship("AuditActivity")
    root_cause: Mapped["RootCause | None"] = relationship("RootCause")
    observation_grading: Mapped["ObservationGrading"] = relationship("ObservationGrading")
    risk_type: Mapped["RiskType"] = relationship("RiskType")
    auditee_record: Mapped["Auditee | None"] = relationship("Auditee", foreign_keys=[auditee_id])
    auditee: Mapped["User | None"] = relationship("User", foreign_keys=[auditee_user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
    action_plans: Mapped[list["ActionPlan"]] = relationship("ActionPlan", back_populates="observation")

    @property
    def auditee_name(self) -> str | None:
        if self.auditee_record:
            return self.auditee_record.full_name
        return self.auditee.full_name if self.auditee else None

    @property
    def auditee_code(self) -> str | None:
        return self.auditee_record.auditee_code if self.auditee_record else None


class ProcessRiskMapping(BaseModel):
    __tablename__ = "process_risk_mappings"
    __table_args__ = (
        Index("ix_process_risk_mappings_audit_plan_id", "audit_plan_id"),
    )

    audit_plan_id: Mapped[int] = mapped_column(ForeignKey("audit_plans.id"), nullable=False)
    process_location_mapping_id: Mapped[int | None] = mapped_column(ForeignKey("process_location_mappings.id"), nullable=True)
    trial_balance_id: Mapped[int | None] = mapped_column(ForeignKey("trial_balances.id"), nullable=True)
    quantitative_assessment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    qualitative_assessment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    final_process_rating: Mapped[str | None] = mapped_column(String(50), nullable=True)

    audit_plan: Mapped[AuditPlan] = relationship(AuditPlan, back_populates="process_risk_mappings")
    process_location_mapping: Mapped["ProcessLocationMapping | None"] = relationship("ProcessLocationMapping")
    trial_balance: Mapped["TrialBalance | None"] = relationship("TrialBalance")


class ERMRisk(BaseModel):
    __tablename__ = "erm_risks"
    __table_args__ = (
        Index("ix_erm_risks_audit_plan_process", "audit_plan_id", "process_id"),
    )

    audit_plan_id: Mapped[int] = mapped_column(ForeignKey("audit_plans.id"), nullable=False)
    erm_risk_code: Mapped[str] = mapped_column(String(100), nullable=False)
    erm_risk_title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[str | None] = mapped_column(String(50), nullable=True)
    process_id: Mapped[int | None] = mapped_column(ForeignKey("processes.id"), nullable=True)

    audit_plan: Mapped[AuditPlan] = relationship(AuditPlan, back_populates="erm_risks")
    process: Mapped["Process | None"] = relationship("Process")


class BusinessInitiative(BaseModel):
    __tablename__ = "business_initiatives"
    __table_args__ = (
        Index("ix_business_initiatives_audit_plan_owner", "audit_plan_id", "owner_user_id"),
    )

    audit_plan_id: Mapped[int] = mapped_column(ForeignKey("audit_plans.id"), nullable=False)
    initiative_code: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    timeline: Mapped[str | None] = mapped_column(String(100), nullable=True)

    audit_plan: Mapped[AuditPlan] = relationship(AuditPlan, back_populates="business_initiatives")
    owner: Mapped["User | None"] = relationship("User")


class OverallAssessment(BaseModel):
    __tablename__ = "overall_assessments"
    __table_args__ = (
        CheckConstraint(
            "coverage_status IN ('Covered', 'Not Covered')",
            name="ck_overall_assessments_coverage_status_valid",
        ),
        Index("ix_overall_assessments_audit_plan_location", "audit_plan_id", "location_id"),
        Index("ix_overall_assessments_coverage_status", "coverage_status"),
    )

    audit_plan_id: Mapped[int] = mapped_column(ForeignKey("audit_plans.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    overall_risk: Mapped[str] = mapped_column(String(50), nullable=False)
    coverage_status: Mapped[str] = mapped_column(String(50), nullable=False)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_audited_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    audit_plan: Mapped[AuditPlan] = relationship(AuditPlan, back_populates="overall_assessments")
    location: Mapped["Location"] = relationship("Location")
