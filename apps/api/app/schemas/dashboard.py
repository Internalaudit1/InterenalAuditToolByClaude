from __future__ import annotations

from pydantic import BaseModel


class KPIItem(BaseModel):
    label: str
    value: int
    trend: str | None = None


class ChartPoint(BaseModel):
    label: str
    value: int


class DashboardSummary(BaseModel):
    total_audits: int
    in_progress: int
    completed: int
    overdue: int
    pending_to_be_initiated: int
    total_action_plans: int
    kpis: list[KPIItem]
    audit_status_summary: list[ChartPoint]
    action_plan_aging: list[ChartPoint]
    severity_distribution: list[ChartPoint]
    location_distribution: list[ChartPoint]

