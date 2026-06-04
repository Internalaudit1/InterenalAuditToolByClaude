from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser
from app.core.enums import RoleCode
from app.core.exceptions import ForbiddenException, NotFoundException


GLOBAL_SCOPE_ROLES = {
    RoleCode.SUPER_ADMIN.value,
    RoleCode.HEAD_AUDITOR.value,
    RoleCode.MANAGEMENT.value,
}


def has_global_scope(current_user: CurrentUser) -> bool:
    return bool(set(current_user.role_codes) & GLOBAL_SCOPE_ROLES)


def apply_company_location_scope(
    stmt: Select,
    current_user: CurrentUser,
    *,
    company_column=None,
    location_column=None,
) -> Select:
    if has_global_scope(current_user):
        return stmt
    if company_column is not None and current_user.company_id:
        stmt = stmt.where(company_column == current_user.company_id)
    if location_column is not None and current_user.location_id:
        stmt = stmt.where(location_column == current_user.location_id)
    return stmt


def assert_company_location_access(
    db: Session,
    model,
    entity_id: int,
    current_user: CurrentUser,
    *,
    company_column_name: str = "company_id",
    location_column_name: str = "location_id",
    not_found_detail: str = "Record not found.",
) -> None:
    stmt = select(model.id).where(model.id == entity_id, model.is_deleted.is_(False))
    company_column = getattr(model, company_column_name, None)
    location_column = getattr(model, location_column_name, None)
    stmt = apply_company_location_scope(stmt, current_user, company_column=company_column, location_column=location_column)
    exists = db.scalar(stmt.limit(1))
    if not exists:
        raise NotFoundException(not_found_detail)


def ensure_same_company_location(
    *,
    current_user: CurrentUser,
    company_id: int | None,
    location_id: int | None,
) -> None:
    if has_global_scope(current_user):
        return
    if current_user.company_id and company_id and current_user.company_id != company_id:
        raise ForbiddenException("You do not have access to this company.")
    if current_user.location_id and location_id and current_user.location_id != location_id:
        raise ForbiddenException("You do not have access to this location.")
