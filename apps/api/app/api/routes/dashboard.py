from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.db.session import get_db
from app.schemas.dashboard import DashboardFilterOptions, DashboardFilters, DashboardSummary
from app.services.dashboard import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    filters: DashboardFilters = Depends(),
    _: CurrentUser = Depends(require_permissions("dashboard:view")),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    return dashboard_service.summary(db, filters)


@router.get("/filter-options", response_model=DashboardFilterOptions)
def get_filter_options(
    _: CurrentUser = Depends(require_permissions("dashboard:view")),
    db: Session = Depends(get_db),
) -> DashboardFilterOptions:
    return dashboard_service.filter_options(db)
