from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, require_permissions
from app.db.session import get_db
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    current_user: CurrentUser = Depends(require_permissions("dashboard:view")),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    return dashboard_service.summary(db)
