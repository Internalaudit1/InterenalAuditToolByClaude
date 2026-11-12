from __future__ import annotations

from pydantic import BaseModel

from app.core.enums import AuditStatus


class KPIItem(BaseModel):
    label: str
    value: int
    trend: str | None = None


class ChartPoint(BaseModel):
    label: str
    value: int


class DashboardFilters(BaseModel):
    fiscal_year: str | None = None
    status: str | None = None
    company_id: int | None = None
    location_id: int | None = None

    def is_empty(self) -> bool:
        return not any([self.fiscal_year, self.status, self.company_id, self.location_id])


class DashboardSummary(BaseModel):
    total_audits: int
    in_progress: int
    completed: int
    overdue: int
    pending_to_be_initiated: int
    unplanned: int = 0
    past_due_count: int = 0
    total_action_plans: int
    kpis: list[KPIItem]
    audit_status_summary: list[ChartPoint]
    action_plan_aging: list[ChartPoint]
    severity_distribution: list[ChartPoint]
    location_distribution: list[ChartPoint]


class FilterOption(BaseModel):
    id: int
    label: str


class LocationFilterOption(FilterOption):
    company_id: int


class DashboardFilterOptions(BaseModel):
    fiscal_years: list[str]
    statuses: list[str]
    companies: list[FilterOption]
    locations: list[LocationFilterOption]

