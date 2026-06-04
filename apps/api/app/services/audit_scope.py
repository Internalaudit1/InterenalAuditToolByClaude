from __future__ import annotations

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser
from app.core.enums import RoleCode
from app.core.exceptions import NotFoundException
from app.models.audit import Audit, AuditMembership


GLOBAL_AUDIT_ROLES = {
    RoleCode.SUPER_ADMIN.value,
    RoleCode.HEAD_AUDITOR.value,
    RoleCode.MANAGEMENT.value,
}


def has_global_audit_visibility(current_user: CurrentUser) -> bool:
    return bool(set(current_user.role_codes) & GLOBAL_AUDIT_ROLES)


def membership_audit_ids_stmt(current_user: CurrentUser):
    return select(AuditMembership.audit_id).where(
        AuditMembership.user_id == current_user.id,
        AuditMembership.is_deleted.is_(False),
    )


def audit_assignment_clause(current_user: CurrentUser, audit_model: type[Audit] = Audit):
    return or_(
        audit_model.id.in_(membership_audit_ids_stmt(current_user)),
        audit_model.audit_owner_id == current_user.id,
        audit_model.reviewer_user_id == current_user.id,
        audit_model.auditee_spoc_user_id == current_user.id,
    )


def apply_audit_scope(stmt: Select, current_user: CurrentUser, audit_model: type[Audit] = Audit) -> Select:
    if has_global_audit_visibility(current_user):
        return stmt
    return stmt.where(audit_assignment_clause(current_user, audit_model))


def assert_can_see_audit(db: Session, audit_id: int, current_user: CurrentUser) -> None:
    if has_global_audit_visibility(current_user):
        exists = db.scalar(select(Audit.id).where(Audit.id == audit_id, Audit.is_deleted.is_(False)))
    else:
        exists = db.scalar(
            select(Audit.id)
            .where(Audit.id == audit_id, Audit.is_deleted.is_(False))
            .where(audit_assignment_clause(current_user))
        )
    if not exists:
        raise NotFoundException("Audit not found.")
