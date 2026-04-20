from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ReportFilters(BaseModel):
    report_type: str | None = None
    company_id: int | None = None
    location_id: int | None = None
    audit_id: int | None = None
    quarter: str | None = None
    status: str | None = None
    criticality: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class ReportRow(BaseModel):
    audit: str
    location: str
    sector: str
    country: str
    quarter: str
    start_date: date
    end_date: date
    status: str
    criticality: str


class ReportSummary(BaseModel):
    rows: list[ReportRow]
    totals: dict[str, int]

