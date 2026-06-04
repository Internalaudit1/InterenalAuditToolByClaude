from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, event, select
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BusinessReferenceCounter(Base):
    __tablename__ = "business_reference_counters"
    __table_args__ = (
        UniqueConstraint("entity_name", "ref_year", name="uq_business_reference_counters_entity_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False)
    ref_year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _extract_year(value: date | datetime | None) -> int:
    if isinstance(value, datetime):
        return value.year
    if isinstance(value, date):
        return value.year
    return datetime.now(UTC).year


def _next_business_reference(connection, *, entity_name: str, prefix: str, ref_year: int, pad_length: int = 4) -> str:
    table = BusinessReferenceCounter.__table__
    row = connection.execute(
        select(table.c.id, table.c.last_value).where(
            table.c.entity_name == entity_name,
            table.c.ref_year == ref_year,
        )
    ).mappings().first()
    now = datetime.now(UTC)
    if row:
        next_value = int(row["last_value"]) + 1
        connection.execute(
            table.update()
            .where(table.c.id == row["id"])
            .values(last_value=next_value, updated_at=now)
        )
    else:
        next_value = 1
        connection.execute(
            table.insert().values(
                entity_name=entity_name,
                ref_year=ref_year,
                last_value=next_value,
                created_at=now,
                updated_at=now,
            )
        )
    return f"{prefix}-{ref_year}-{next_value:0{pad_length}d}"


def _is_postgresql(connection) -> bool:
    return connection.dialect.name == "postgresql"


from app.models.action_plan import ActionPlan, ActionPlanRevision  # noqa: E402
from app.models.audit import Audit, AuditPlan, Observation  # noqa: E402
from app.models.engagement import EngagementPlan  # noqa: E402
from app.models.support import Attachment  # noqa: E402
from app.models.workpaper import EvidenceRegister, Workpaper  # noqa: E402


@event.listens_for(AuditPlan, "before_insert")
def generate_audit_plan_number(_mapper, connection, target: AuditPlan) -> None:
    if _is_postgresql(connection):
        return
    target.audit_number = _next_business_reference(
        connection,
        entity_name="audit_number",
        prefix="AUD",
        ref_year=_extract_year(target.start_date),
    )


@event.listens_for(EngagementPlan, "before_insert")
def generate_engagement_code(_mapper, connection, target: EngagementPlan) -> None:
    if _is_postgresql(connection):
        return
    target.engagement_code = _next_business_reference(
        connection,
        entity_name="engagement_plan",
        prefix="ENG",
        ref_year=_extract_year(target.planned_start_date),
    )


@event.listens_for(Audit, "before_insert")
def generate_audit_number(_mapper, connection, target: Audit) -> None:
    if _is_postgresql(connection):
        return
    if target.audit_plan_id:
        audit_plan_number = connection.execute(
            select(AuditPlan.__table__.c.audit_number).where(AuditPlan.__table__.c.id == target.audit_plan_id)
        ).scalar_one_or_none()
        if _normalize_text(audit_plan_number):
            target.audit_number = audit_plan_number
            return
    target.audit_number = _next_business_reference(
        connection,
        entity_name="audit_number",
        prefix="AUD",
        ref_year=_extract_year(target.start_date),
    )


@event.listens_for(ActionPlan, "before_insert")
def generate_action_plan_references(_mapper, connection, target: ActionPlan) -> None:
    if _is_postgresql(connection):
        return
    ref_year = datetime.now(UTC).year
    if not _normalize_text(target.audit_number) and target.audit_id:
        audit_number = connection.execute(
            select(Audit.__table__.c.audit_number).where(Audit.__table__.c.id == target.audit_id)
        ).scalar_one_or_none()
        if _normalize_text(audit_number):
            target.audit_number = audit_number
    target.action_plan_id = _next_business_reference(connection, entity_name="action_plan", prefix="ACT", ref_year=ref_year)
    target.observation_number = _next_business_reference(connection, entity_name="observation", prefix="OBS", ref_year=ref_year)


@event.listens_for(Observation, "before_insert")
def generate_observation_number(_mapper, connection, target: Observation) -> None:
    if _is_postgresql(connection):
        return
    if _normalize_text(target.observation_number):
        return
    target.observation_number = _next_business_reference(
        connection,
        entity_name="observation",
        prefix="OBS",
        ref_year=datetime.now(UTC).year,
    )


@event.listens_for(ActionPlanRevision, "before_insert")
def generate_revision_response_code(_mapper, connection, target: ActionPlanRevision) -> None:
    if _is_postgresql(connection):
        return
    if _normalize_text(target.response_code):
        return
    target.response_code = _next_business_reference(
        connection,
        entity_name="management_response",
        prefix="MRG",
        ref_year=datetime.now(UTC).year,
    )


@event.listens_for(Attachment, "before_insert")
def generate_attachment_evidence_code(_mapper, connection, target: Attachment) -> None:
    if _is_postgresql(connection):
        return
    if _normalize_text(target.evidence_code):
        return
    target.evidence_code = _next_business_reference(
        connection,
        entity_name="attachment",
        prefix="EVD",
        ref_year=datetime.now(UTC).year,
    )


@event.listens_for(Workpaper, "before_insert")
def generate_workpaper_code(_mapper, connection, target: Workpaper) -> None:
    if _is_postgresql(connection):
        return
    if _normalize_text(target.workpaper_code):
        return
    target.workpaper_code = _next_business_reference(
        connection,
        entity_name="workpaper",
        prefix="WP",
        ref_year=datetime.now(UTC).year,
    )


@event.listens_for(EvidenceRegister, "before_insert")
def generate_evidence_register_code(_mapper, connection, target: EvidenceRegister) -> None:
    if _is_postgresql(connection):
        return
    if _normalize_text(target.evidence_code):
        return
    target.evidence_code = _next_business_reference(
        connection,
        entity_name="evidence_register",
        prefix="EVR",
        ref_year=datetime.now(UTC).year,
    )
