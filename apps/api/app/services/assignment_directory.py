from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import RoleCode
from app.core.exceptions import ValidationException
from app.models import Auditee, Role, User, UserRole


INTERNAL_ASSIGNMENT_ROLE_CODES = {
    RoleCode.SUPER_ADMIN.value,
    RoleCode.HEAD_AUDITOR.value,
    RoleCode.AUDITOR.value,
    RoleCode.JUNIOR_AUDITOR.value,
    RoleCode.MANAGEMENT.value,
}


class AssignmentDirectoryService:
    def get_active_user(self, db: Session, user_id: int) -> User:
        user = db.scalar(
            select(User)
            .options(joinedload(User.role_links).joinedload(UserRole.role))
            .where(User.id == user_id, User.is_deleted.is_(False), User.is_active.is_(True))
        )
        if not user:
            raise ValidationException("Selected user was not found or is inactive.")
        return user

    def get_user_role_codes(self, user: User) -> set[str]:
        return {link.role.code for link in user.role_links if link.role and not link.role.is_deleted}

    def validate_internal_user(self, db: Session, user_id: int | None, label: str) -> User | None:
        if not user_id:
            return None
        user = self.get_active_user(db, user_id)
        role_codes = self.get_user_role_codes(user)
        if not role_codes.intersection(INTERNAL_ASSIGNMENT_ROLE_CODES):
            raise ValidationException(f"{label} must be an active internal user with an auditor-facing role.")
        return user

    def validate_auditee_user(self, db: Session, user_id: int | None, label: str = "Auditee user") -> User | None:
        if not user_id:
            return None
        user = self.get_active_user(db, user_id)
        role_codes = self.get_user_role_codes(user)
        if RoleCode.AUDITEE.value not in role_codes:
            raise ValidationException(f"{label} must be linked to an active user with the auditee role.")
        return user

    def get_active_auditee(self, db: Session, auditee_id: int) -> Auditee:
        auditee = db.scalar(
            select(Auditee)
            .options(joinedload(Auditee.linked_user).joinedload(User.role_links).joinedload(UserRole.role))
            .where(Auditee.id == auditee_id, Auditee.is_deleted.is_(False), Auditee.is_active.is_(True))
        )
        if not auditee:
            raise ValidationException("Selected auditee was not found or is inactive.")
        return auditee

    def resolve_auditee(self, db: Session, auditee_id: int | None, *, require_linked_user: bool, label: str = "Auditee") -> Auditee | None:
        if not auditee_id:
            return None
        auditee = self.get_active_auditee(db, auditee_id)
        if require_linked_user:
            if not auditee.linked_user_id:
                raise ValidationException(f"{label} must have a linked portal user before this workflow step.")
            self.validate_auditee_user(db, auditee.linked_user_id, label=f"{label} linked user")
        elif auditee.linked_user_id:
            self.validate_auditee_user(db, auditee.linked_user_id, label=f"{label} linked user")
        return auditee

    def apply_auditee_selection(
        self,
        db: Session,
        data: dict,
        *,
        auditee_field: str,
        user_field: str,
        require_linked_user: bool,
        allow_direct_user_fallback: bool = True,
        label: str = "Auditee",
    ) -> None:
        auditee_id = data.get(auditee_field)
        user_id = data.get(user_field)
        if auditee_id:
            auditee = self.resolve_auditee(db, int(auditee_id), require_linked_user=require_linked_user, label=label)
            data[user_field] = auditee.linked_user_id if auditee else None
            return
        if user_id and allow_direct_user_fallback:
            self.validate_auditee_user(db, int(user_id), label=f"{label} user")
            return
        if require_linked_user and user_id is None:
            raise ValidationException(f"{label} is required before this workflow step.")

    def search_auditees(
        self,
        db: Session,
        *,
        q: str | None = None,
        page_size: int = 20,
        active_only: bool = True,
        company_id: int | None = None,
        location_id: int | None = None,
        linked_user_required: bool = False,
    ) -> list[Auditee]:
        stmt = select(Auditee).where(Auditee.is_deleted.is_(False))
        if active_only:
            stmt = stmt.where(Auditee.is_active.is_(True))
        if company_id:
            stmt = stmt.where(Auditee.company_id == company_id)
        if location_id:
            stmt = stmt.where(Auditee.location_id == location_id)
        if linked_user_required:
            stmt = stmt.where(Auditee.linked_user_id.is_not(None))
        if q:
            stmt = stmt.where(
                or_(
                    Auditee.auditee_code.ilike(f"%{q}%"),
                    Auditee.full_name.ilike(f"%{q}%"),
                    Auditee.email.ilike(f"%{q}%"),
                    Auditee.department.ilike(f"%{q}%"),
                    Auditee.designation.ilike(f"%{q}%"),
                )
            )
        stmt = stmt.order_by(Auditee.full_name.asc(), Auditee.auditee_code.asc()).limit(page_size)
        return list(db.scalars(stmt).all())


assignment_directory_service = AssignmentDirectoryService()
