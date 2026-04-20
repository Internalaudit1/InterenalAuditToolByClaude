from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction
from app.models.audit import Audit
from app.schemas.reporting import ReportFilters, ReportRow, ReportSummary
from app.services.activity_log import activity_log_service


class ReportingService:
    def get_rows(self, db: Session, filters: ReportFilters) -> list[Audit]:
        stmt = select(Audit).where(Audit.is_deleted.is_(False))
        if filters.audit_id:
            stmt = stmt.where(Audit.id == filters.audit_id)
        if filters.company_id:
            stmt = stmt.where(Audit.company_id == filters.company_id)
        if filters.location_id:
            stmt = stmt.where(Audit.location_id == filters.location_id)
        if filters.quarter:
            stmt = stmt.where(Audit.quarter == filters.quarter)
        if filters.status:
            stmt = stmt.where(Audit.status == filters.status)
        if filters.criticality:
            stmt = stmt.where(Audit.criticality == filters.criticality)
        if filters.start_date and filters.end_date:
            stmt = stmt.where(and_(Audit.start_date >= filters.start_date, Audit.end_date <= filters.end_date))
        return list(db.scalars(stmt).all())

    def build_summary(self, audits: list[Audit]) -> ReportSummary:
        rows = [
            ReportRow(
                audit=audit.audit_name,
                location=audit.location.description,
                sector=audit.location.sector,
                country=audit.location.country.name,
                quarter=audit.quarter,
                start_date=audit.start_date,
                end_date=audit.end_date,
                status=audit.status,
                criticality=audit.criticality,
            )
            for audit in audits
        ]
        totals = {
            "count": len(rows),
            "completed": sum(1 for row in rows if row.status == "Completed"),
            "in_progress": sum(1 for row in rows if row.status == "In Progress"),
            "overdue": sum(1 for row in rows if row.status == "Overdue"),
        }
        return ReportSummary(rows=rows, totals=totals)

    def export_excel(self, report: ReportSummary) -> bytes:
        wb = Workbook()
        ws = wb.active
        ws.title = "Reports"
        ws.append(["Audit", "Location", "Sector", "Country", "Quarter", "Start Date", "End Date", "Status", "Criticality"])
        for row in report.rows:
            ws.append(
                [
                    row.audit,
                    row.location,
                    row.sector,
                    row.country,
                    row.quarter,
                    row.start_date.isoformat(),
                    row.end_date.isoformat(),
                    row.status,
                    row.criticality,
                ]
            )
        stream = BytesIO()
        wb.save(stream)
        return stream.getvalue()

    def export_pdf(self, report: ReportSummary) -> bytes:
        stream = BytesIO()
        pdf = canvas.Canvas(stream, pagesize=A4)
        pdf.drawString(50, 800, "HCL Internal Audit Report")
        pdf.drawString(50, 785, f"Total records: {report.totals['count']}")
        y = 760
        for row in report.rows[:25]:
            pdf.drawString(50, y, f"{row.audit} | {row.location} | {row.status} | {row.criticality}")
            y -= 18
            if y < 50:
                pdf.showPage()
                y = 800
        pdf.save()
        return stream.getvalue()

    def log_export(self, db: Session, *, actor_user_id: int | None, actor_name: str, format_name: str) -> None:
        activity_log_service.log(
            db,
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            role=None,
            module="reports",
            entity_type="report",
            entity_id=format_name,
            action_type=ActivityAction.EXPORT.value,
            new_values={"format": format_name},
        )


reporting_service = ReportingService()
