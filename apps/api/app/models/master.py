from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ActiveMixin, BaseModel


class ReferenceDataMixin:
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Country(ActiveMixin, BaseModel, ReferenceDataMixin):
    __tablename__ = "countries"

    states: Mapped[list["State"]] = relationship("State", back_populates="country")
    companies: Mapped[list["Company"]] = relationship("Company", back_populates="country")
    locations: Mapped[list["Location"]] = relationship("Location", back_populates="country")


class State(ActiveMixin, BaseModel, ReferenceDataMixin):
    __tablename__ = "states"

    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False)

    country: Mapped[Country] = relationship(Country, back_populates="states")
    cities: Mapped[list["City"]] = relationship("City", back_populates="state")
    companies: Mapped[list["Company"]] = relationship("Company", back_populates="state")
    locations: Mapped[list["Location"]] = relationship("Location", back_populates="state")


class City(ActiveMixin, BaseModel, ReferenceDataMixin):
    __tablename__ = "cities"

    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), nullable=False)

    state: Mapped[State] = relationship(State, back_populates="cities")
    companies: Mapped[list["Company"]] = relationship("Company", back_populates="city")
    locations: Mapped[list["Location"]] = relationship("Location", back_populates="city")


class Company(ActiveMixin, BaseModel):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False)
    pan: Mapped[str] = mapped_column(String(50), nullable=False)
    gst_no: Mapped[str] = mapped_column(String(50), nullable=False)
    approver_config: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)

    country: Mapped[Country] = relationship(Country, back_populates="companies")
    state: Mapped[State] = relationship(State, back_populates="companies")
    city: Mapped[City] = relationship(City, back_populates="companies")
    locations: Mapped[list["Location"]] = relationship("Location", back_populates="company")
    users: Mapped[list["User"]] = relationship("User", back_populates="company")
    auditees: Mapped[list["Auditee"]] = relationship("Auditee", back_populates="company")


class Process(ActiveMixin, BaseModel):
    __tablename__ = "processes"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    business_cycle: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    mappings: Mapped[list["ProcessLocationMapping"]] = relationship("ProcessLocationMapping", back_populates="process")


class Location(ActiveMixin, BaseModel):
    __tablename__ = "locations"

    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    division_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    division_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    location_code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    risk_index: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    country: Mapped[Country] = relationship(Country, back_populates="locations")
    state: Mapped[State] = relationship(State, back_populates="locations")
    city: Mapped[City] = relationship(City, back_populates="locations")
    company: Mapped[Company] = relationship(Company, back_populates="locations")
    mappings: Mapped[list["ProcessLocationMapping"]] = relationship("ProcessLocationMapping", back_populates="location")
    users: Mapped[list["User"]] = relationship("User", back_populates="location")
    auditees: Mapped[list["Auditee"]] = relationship("Auditee", back_populates="location")


class ProcessLocationMapping(ActiveMixin, BaseModel):
    __tablename__ = "process_location_mappings"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    audit_name: Mapped[str] = mapped_column(String(255), nullable=False)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    trial_balance_id: Mapped[int | None] = mapped_column(ForeignKey("trial_balances.id"), nullable=True)

    __table_args__ = (
        Index("ix_process_location_mappings_process_location", "process_id", "location_id"),
    )

    process: Mapped[Process] = relationship(Process, back_populates="mappings")
    location: Mapped[Location] = relationship(Location, back_populates="mappings")
    company: Mapped[Company] = relationship(Company)
    trial_balance: Mapped["TrialBalance | None"] = relationship("TrialBalance", back_populates="process_location_mappings")


class RiskType(ActiveMixin, BaseModel, ReferenceDataMixin):
    __tablename__ = "risk_types"


class ReportConsideration(ActiveMixin, BaseModel, ReferenceDataMixin):
    __tablename__ = "report_considerations"


class Recommendation(ActiveMixin, BaseModel, ReferenceDataMixin):
    __tablename__ = "recommendations"


class RootCause(ActiveMixin, BaseModel, ReferenceDataMixin):
    __tablename__ = "root_causes"


class Impact(ActiveMixin, BaseModel, ReferenceDataMixin):
    __tablename__ = "impacts"


class TrialBalance(ActiveMixin, BaseModel):
    __tablename__ = "trial_balances"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    company: Mapped[Company | None] = relationship(Company)
    process_location_mappings: Mapped[list[ProcessLocationMapping]] = relationship(
        ProcessLocationMapping,
        back_populates="trial_balance",
    )


class ObservationGrading(ActiveMixin, BaseModel):
    __tablename__ = "observation_gradings"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    severity_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("severity_rank > 0", name="ck_observation_gradings_severity_rank_positive"),
    )


class AuditEscalation(ActiveMixin, BaseModel):
    __tablename__ = "audit_escalations"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    escalation_days: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Designation(ActiveMixin, BaseModel):
    __tablename__ = "designations"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    users: Mapped[list["User"]] = relationship("User", back_populates="designation")


class Auditee(ActiveMixin, BaseModel):
    __tablename__ = "auditees"

    auditee_code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    linked_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    company: Mapped[Company | None] = relationship(Company, back_populates="auditees")
    location: Mapped[Location | None] = relationship(Location, back_populates="auditees")
    linked_user: Mapped["User | None"] = relationship("User", foreign_keys=[linked_user_id], back_populates="linked_auditee_records")
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])

    @property
    def display_name(self) -> str:
        return self.full_name

    @property
    def linked_user_name(self) -> str | None:
        return self.linked_user.full_name if self.linked_user else None


class ControlPerformanceIndicator(ActiveMixin, BaseModel):
    __tablename__ = "control_performance_indicators"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    threshold: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class TaskSwapRule(ActiveMixin, BaseModel):
    __tablename__ = "task_swap_rules"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    source_designation_id: Mapped[int | None] = mapped_column(ForeignKey("designations.id"), nullable=True)
    target_designation_id: Mapped[int | None] = mapped_column(ForeignKey("designations.id"), nullable=True)
    max_tasks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_designation: Mapped[Designation | None] = relationship(Designation, foreign_keys=[source_designation_id])
    target_designation: Mapped[Designation | None] = relationship(Designation, foreign_keys=[target_designation_id])
