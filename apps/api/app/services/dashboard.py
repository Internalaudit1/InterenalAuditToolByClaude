from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core.enums import AuditStatus
from app.models.action_plan import ActionPlan
from app.models.audit import Audit
from app.models.master import Location, ObservationGrading
from app.schemas.dashboard import ChartPoint, DashboardSummary, KPIItem


class DashboardService:
    def summary(self, db: Session) -> DashboardSummary:
        audit_row = db.execute(
            select(
                func.count(Audit.id),
                func.sum(case((Audit.status == AuditStatus.IN_PROGRESS.value, 1), else_=0)),
                func.sum(case((Audit.status == AuditStatus.COMPLETED.value, 1), else_=0)),
                func.sum(case((Audit.status == AuditStatus.TO_BE_INITIATED.value, 1), else_=0)),
                func.sum(case((and_(Audit.end_date < date.today(), Audit.status != AuditStatus.COMPLETED.value), 1), else_=0)),
            )
        ).one()
        total_audits, in_progress, completed, pending, overdue = [value or 0 for value in audit_row]
        total_action_plans = db.scalar(select(func.count(ActionPlan.id))) or 0
        due_limit = date.today() + timedelta(days=7)

        audit_status_summary = [
            ChartPoint(label=status, value=count or 0)
            for status, count in db.execute(select(Audit.status, func.count(Audit.id)).group_by(Audit.status)).all()
        ]
        action_plan_aging = [
            ChartPoint(label="Overdue", value=db.scalar(select(func.count(ActionPlan.id)).where(ActionPlan.agreed_timeline < date.today())) or 0),
            ChartPoint(
                label="Due in 7 days",
                value=db.scalar(
                    select(func.count(ActionPlan.id)).where(
                        and_(ActionPlan.agreed_timeline >= date.today(), ActionPlan.agreed_timeline <= due_limit)
                    )
                )
                or 0,
            ),
        ]
        severity_distribution = [
            ChartPoint(label=label or "Unclassified", value=count or 0)
            for label, count in db.execute(
                select(ObservationGrading.name, func.count(ActionPlan.id))
                .join(ActionPlan, ActionPlan.observation_grading_id == ObservationGrading.id)
                .group_by(ObservationGrading.name)
            ).all()
        ]
        location_distribution = [
            ChartPoint(label=label or "Unknown", value=count or 0)
            for label, count in db.execute(
                select(Location.description, func.count(Audit.id)).join(Audit, Audit.location_id == Location.id).group_by(Location.description)
            ).all()
        ]

        return DashboardSummary(
            total_audits=total_audits,
            in_progress=in_progress,
            completed=completed,
            overdue=overdue,
            pending_to_be_initiated=pending,
            total_action_plans=total_action_plans,
            kpis=[
                KPIItem(label="Total Audits", value=total_audits),
                KPIItem(label="In Progress", value=in_progress),
                KPIItem(label="Completed", value=completed),
                KPIItem(label="Overdue", value=overdue),
                KPIItem(label="Pending to be initiated", value=pending),
                KPIItem(label="Total Action Plans", value=total_action_plans),
            ],
            audit_status_summary=audit_status_summary,
            action_plan_aging=action_plan_aging,
            severity_distribution=severity_distribution,
            location_distribution=location_distribution,
        )


dashboard_service = DashboardService()

