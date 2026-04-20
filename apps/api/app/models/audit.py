from __future__ import annotations

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AuditPlan(BaseModel):
    __tablename__ = "audit_plans"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_audit_plans_date_range"),
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
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    company: Mapped["Company"] = relationship("Company")
    location: Mapped["Location"] = relationship("Location")
    audit_owner: Mapped["User | None"] = relationship("User")
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
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    history_timeline: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)

    audit_plan: Mapped[AuditPlan | None] = relationship(AuditPlan, back_populates="audit")
    company: Mapped["Company"] = relationship("Company")
    location: Mapped["Location"] = relationship("Location")
    audit_owner: Mapped["User | None"] = relationship("User")
    action_plans: Mapped[list["ActionPlan"]] = relationship("ActionPlan", back_populates="audit")


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
