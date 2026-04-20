from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.db.session import get_db
from app.schemas.reporting import ReportFilters, ReportSummary
from app.services.reporting import reporting_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=ReportSummary)
def list_reports(
    filters: ReportFilters = Depends(),
    _: CurrentUser = Depends(require_permissions("reports:view")),
    db: Session = Depends(get_db),
):
    audits = reporting_service.get_rows(db, filters)
    return reporting_service.build_summary(audits)


@router.get("/export/excel")
def export_excel(
    filters: ReportFilters = Depends(),
    current_user: CurrentUser = Depends(require_permissions("reports:export")),
    db: Session = Depends(get_db),
):
    report = reporting_service.build_summary(reporting_service.get_rows(db, filters))
    content = reporting_service.export_excel(report)
    reporting_service.log_export(db, actor_user_id=current_user.id, actor_name=current_user.full_name, format_name="excel")
    db.commit()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="dia-report.xlsx"'},
    )


@router.get("/export/pdf")
def export_pdf(
    filters: ReportFilters = Depends(),
    current_user: CurrentUser = Depends(require_permissions("reports:export")),
    db: Session = Depends(get_db),
):
    report = reporting_service.build_summary(reporting_service.get_rows(db, filters))
    content = reporting_service.export_pdf(report)
    reporting_service.log_export(db, actor_user_id=current_user.id, actor_name=current_user.full_name, format_name="pdf")
    db.commit()
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="dia-report.pdf"'})

