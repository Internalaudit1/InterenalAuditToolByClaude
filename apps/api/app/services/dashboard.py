from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core.enums import ActionPlanStatus, AuditStatus
from app.core.exceptions import ValidationException
from app.models.action_plan import ActionPlan
from app.models.audit import Audit, AuditPlan
from app.models.master import Company, Location, ObservationGrading
from app.schemas.dashboard import (
    ChartPoint,
    DashboardFilterOptions,
    DashboardFilters,
    DashboardSummary,
    FilterOption,
    KPIItem,
    LocationFilterOption,
)


class DashboardService:
    def _audit_predicates(self, filters: DashboardFilters) -> list:
        """Predicates applied to every dashboard metric so cards and charts always agree.

        Note: these come straight from the query string. If per-company row scoping is ever
        introduced, intersect them with the caller's allowed scope instead of trusting them.
        """
        predicates = [Audit.is_deleted.is_(False)]
        if filters.status and filters.status not in {status.value for status in AuditStatus}:
            # A mistyped status would otherwise render an all-zero dashboard that looks like real data.
            allowed = ", ".join(status.value for status in AuditStatus)
            raise ValidationException(f"Audit Status must be one of: {allowed}.")
        if filters.fiscal_year:
            predicates.append(Audit.fiscal_year == filters.fiscal_year)
        if filters.status:
            predicates.append(Audit.status == filters.status)
        if filters.company_id:
            predicates.append(Audit.company_id == filters.company_id)
        if filters.location_id:
            predicates.append(Audit.location_id == filters.location_id)
        return predicates

    def summary(self, db: Session, filters: DashboardFilters | None = None) -> DashboardSummary:
        filters = filters or DashboardFilters()
        predicates = self._audit_predicates(filters)
        today = date.today()
        due_limit = today + timedelta(days=7)

        # One status aggregation feeds the chart, the totals and every status card, so the
        # cards can never disagree with the chart the way they did before.
        rows = db.execute(
            select(Audit.status, func.count(Audit.id)).where(*predicates).group_by(Audit.status)
        ).all()
        counts = {status: count or 0 for status, count in rows}
        audit_status_summary = [
            ChartPoint(label=status.value, value=counts.pop(status.value, 0)) for status in AuditStatus
        ]
        # Any status outside the enum (legacy rows) still counts toward the total.
        audit_status_summary += [ChartPoint(label=label, value=value) for label, value in sorted(counts.items())]
        total_audits = sum(point.value for point in audit_status_summary)

        in_progress = self._status_count(audit_status_summary, AuditStatus.IN_PROGRESS)
        completed = self._status_count(audit_status_summary, AuditStatus.COMPLETED)
        pending = self._status_count(audit_status_summary, AuditStatus.TO_BE_INITIATED)
        overdue = self._status_count(audit_status_summary, AuditStatus.OVERDUE)
        unplanned = self._status_count(audit_status_summary, AuditStatus.UNPLANNED)

        # Separate risk metric: past the end date and not signed off, whatever the workflow status says.
        past_due_count = db.scalar(
            select(func.count(Audit.id)).where(
                *predicates,
                Audit.end_date < today,
                Audit.status != AuditStatus.COMPLETED.value,
            )
        ) or 0

        # Action plans carry no fiscal year/company of their own, so every action-plan metric is
        # scoped through its audit. audit_id is NOT NULL, so this inner join drops no live rows.
        action_plan_scope = [*predicates, ActionPlan.is_deleted.is_(False)]
        total_action_plans = db.scalar(
            select(func.count(ActionPlan.id))
            .join(Audit, ActionPlan.audit_id == Audit.id)
            .where(*action_plan_scope)
        ) or 0

        aging_row = db.execute(
            select(
                func.sum(case((ActionPlan.agreed_timeline < today, 1), else_=0)),
                func.sum(
                    case(
                        (and_(ActionPlan.agreed_timeline >= today, ActionPlan.agreed_timeline <= due_limit), 1),
                        else_=0,
                    )
                ),
            )
            .join(Audit, ActionPlan.audit_id == Audit.id)
            .where(*action_plan_scope, ActionPlan.auditor_status != ActionPlanStatus.COMPLETED.value)
        ).one()
        action_plan_aging = [
            ChartPoint(label="Overdue", value=aging_row[0] or 0),
            ChartPoint(label="Due in 7 days", value=aging_row[1] or 0),
        ]

        severity_distribution = [
            ChartPoint(label=label, value=count or 0)
            for label, count in db.execute(
                select(ObservationGrading.name, func.count(ActionPlan.id))
                .join(ActionPlan, ActionPlan.observation_grading_id == ObservationGrading.id)
                .join(Audit, ActionPlan.audit_id == Audit.id)
                .where(*action_plan_scope, ObservationGrading.is_deleted.is_(False))
                .group_by(ObservationGrading.name, ObservationGrading.severity_rank)
                .order_by(ObservationGrading.severity_rank)
            ).all()
        ]

        location_distribution = [
            ChartPoint(label=label or "Unknown", value=count or 0)
            for label, count in db.execute(
                select(Location.description, func.count(Audit.id))
                .join(Audit, Audit.location_id == Location.id)
                .where(*predicates, Location.is_deleted.is_(False))
                .group_by(Location.description)
            ).all()
        ]

        return DashboardSummary(
            total_audits=total_audits,
            in_progress=in_progress,
            completed=completed,
            overdue=overdue,
            pending_to_be_initiated=pending,
            unplanned=unplanned,
            past_due_count=past_due_count,
            total_action_plans=total_action_plans,
            kpis=[
                KPIItem(label="Total Audits", value=total_audits),
                KPIItem(label=AuditStatus.TO_BE_INITIATED.value, value=pending),
                KPIItem(label=AuditStatus.IN_PROGRESS.value, value=in_progress),
                KPIItem(label=AuditStatus.COMPLETED.value, value=completed),
                KPIItem(label=AuditStatus.OVERDUE.value, value=overdue),
                KPIItem(label=AuditStatus.UNPLANNED.value, value=unplanned),
                KPIItem(label="Total Action Plans", value=total_action_plans),
            ],
            audit_status_summary=audit_status_summary,
            action_plan_aging=action_plan_aging,
            severity_distribution=severity_distribution,
            location_distribution=location_distribution,
        )

    def filter_options(self, db: Session) -> DashboardFilterOptions:
        """Dropdown values for the dashboard filter bar.

        Served here rather than from /master/* because the Management role holds
        dashboard:view but not masters:view.
        """
        audit_years = db.scalars(
            select(Audit.fiscal_year).where(Audit.is_deleted.is_(False), Audit.fiscal_year.is_not(None)).distinct()
        ).all()
        plan_years = db.scalars(
            select(AuditPlan.fiscal_year)
            .where(AuditPlan.is_deleted.is_(False), AuditPlan.fiscal_year.is_not(None))
            .distinct()
        ).all()
        fiscal_years = sorted({year for year in [*audit_years, *plan_years] if year}, reverse=True)

        companies = [
            FilterOption(id=company_id, label=name)
            for company_id, name in db.execute(
                select(Company.id, Company.name)
                .where(Company.is_deleted.is_(False), Company.is_active.is_(True))
                .order_by(Company.name)
            ).all()
        ]
        locations = [
            LocationFilterOption(id=location_id, label=description or code or f"Location {location_id}", company_id=company_id)
            for location_id, description, code, company_id in db.execute(
                select(Location.id, Location.description, Location.location_code, Location.company_id)
                .where(Location.is_deleted.is_(False), Location.is_active.is_(True))
                .order_by(Location.description)
            ).all()
        ]

        return DashboardFilterOptions(
            fiscal_years=fiscal_years,
            # Static, so a status stays selectable when it currently has zero rows.
            statuses=[status.value for status in AuditStatus],
            companies=companies,
            locations=locations,
        )

    def _status_count(self, points: list[ChartPoint], status: AuditStatus) -> int:
        return next((point.value for point in points if point.label == status.value), 0)


dashboard_service = DashboardService()
