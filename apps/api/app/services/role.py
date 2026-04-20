from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import ActivityAction, RoleCode
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.auth import Permission, Role, User, UserRole
from app.repositories.base import BaseRepository
from app.schemas.role import RoleCreate, RolePermissionUpdate, RoleUpdate
from app.services.activity_log import activity_log_service
from app.utils.serialization import model_to_dict

SYSTEM_ROLE_CODES = {role.value for role in RoleCode}
ROLE_MANAGEMENT_PERMISSION_CODES = {"roles:view", "roles:manage"}
SUPER_ADMIN_PROTECTED_PERMISSION_CODES = {"roles:view", "roles:manage", "users:view", "users:manage"}


class RoleService:
    role_repo = BaseRepository(Role)

    def list_permissions(self, db: Session) -> list[Permission]:
        stmt = select(Permission).where(Permission.is_deleted.is_(False)).order_by(Permission.code)
        return list(db.scalars(stmt).all())

    def list_roles(self, db: Session, *, actor_role_codes: list[str] | None = None) -> list[Role]:
        stmt = (
            select(Role)
            .options(joinedload(Role.permissions), joinedload(Role.user_links).joinedload(UserRole.user))
            .where(Role.is_deleted.is_(False))
            .order_by(Role.is_system.desc(), Role.name)
        )
        roles = list(db.execute(stmt).unique().scalars().all())
        if actor_role_codes and RoleCode.SUPER_ADMIN.value not in actor_role_codes:
            return [role for role in roles if role.code != RoleCode.SUPER_ADMIN.value]
        return roles

    def get_role(self, db: Session, role_id: int) -> Role:
        stmt = (
            select(Role)
            .options(joinedload(Role.permissions), joinedload(Role.user_links).joinedload(UserRole.user))
            .where(Role.id == role_id, Role.is_deleted.is_(False))
        )
        role = db.execute(stmt).unique().scalar_one_or_none()
        if not role:
            raise NotFoundException("Role not found.")
        return role

    def create_role(self, db: Session, payload: RoleCreate, actor_name: str, actor_id: int | None) -> Role:
        code = payload.code.strip().lower()
        if code in SYSTEM_ROLE_CODES:
            raise ConflictException("System role codes are reserved.")
        existing = db.scalar(select(Role).where(Role.code == code, Role.is_deleted.is_(False)))
        if existing:
            raise ConflictException("Role code already exists.")

        role = Role(
            code=code,
            name=payload.name.strip(),
            description=payload.description,
            is_system=False,
            created_by=actor_name,
            updated_by=actor_name,
        )
        role.permissions = self._resolve_assignable_permissions(db, code, payload.permission_codes)
        db.add(role)
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=RoleCode.SUPER_ADMIN.value,
            module="admin",
            entity_type="role",
            entity_id=str(role.id),
            action_type=ActivityAction.CREATE.value,
            new_values=self._snapshot(role),
        )
        return role

    def update_role(self, db: Session, role_id: int, payload: RoleUpdate, actor_name: str, actor_id: int | None) -> Role:
        role = self.get_role(db, role_id)
        before = self._snapshot(role)
        data = payload.model_dump(exclude_none=True)
        if "name" in data:
            role.name = data["name"].strip()
        if "description" in data:
            role.description = data["description"]
        role.updated_by = actor_name
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=RoleCode.SUPER_ADMIN.value,
            module="admin",
            entity_type="role",
            entity_id=str(role.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=self._snapshot(role),
        )
        return role

    def update_permissions(self, db: Session, role_id: int, payload: RolePermissionUpdate, actor_name: str, actor_id: int | None) -> Role:
        role = self.get_role(db, role_id)
        if role.code == RoleCode.SUPER_ADMIN.value:
            raise ValidationException("Super Admin permissions are protected and cannot be edited.")
        before = self._snapshot(role)
        role.permissions = self._resolve_assignable_permissions(db, role.code, payload.permission_codes)
        role.updated_by = actor_name
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=RoleCode.SUPER_ADMIN.value,
            module="admin",
            entity_type="role",
            entity_id=str(role.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=self._snapshot(role),
        )
        return role

    def delete_role(self, db: Session, role_id: int, actor_name: str, actor_id: int | None) -> None:
        role = self.get_role(db, role_id)
        if role.is_system:
            raise ConflictException("System roles cannot be deleted.")
        active_assignment_count = db.scalar(
            select(func.count())
            .select_from(UserRole)
            .join(User, User.id == UserRole.user_id)
            .where(UserRole.role_id == role.id, User.is_deleted.is_(False))
        ) or 0
        if active_assignment_count:
            raise ConflictException("This role cannot be deleted because it is assigned to active users.")
        before = self._snapshot(role)
        self.role_repo.soft_delete(db, role, actor_name=actor_name)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=RoleCode.SUPER_ADMIN.value,
            module="admin",
            entity_type="role",
            entity_id=str(role.id),
            action_type=ActivityAction.DELETE.value,
            old_values=before,
            new_values={"is_deleted": True},
        )

    def _resolve_assignable_permissions(self, db: Session, role_code: str, permission_codes: list[str]) -> list[Permission]:
        unique_codes = sorted(set(permission_codes))
        if role_code != RoleCode.SUPER_ADMIN.value and ROLE_MANAGEMENT_PERMISSION_CODES.intersection(unique_codes):
            raise ValidationException("Role-management permissions can only belong to Super Admin.")
        if role_code == RoleCode.SUPER_ADMIN.value and not SUPER_ADMIN_PROTECTED_PERMISSION_CODES.issubset(unique_codes):
            raise ValidationException("Super Admin must retain core administration permissions.")

        permissions = list(db.scalars(select(Permission).where(Permission.code.in_(unique_codes), Permission.is_deleted.is_(False))).all())
        if len(permissions) != len(unique_codes):
            raise ValidationException("One or more permissions are invalid.")
        return sorted(permissions, key=lambda permission: permission.code)

    def _snapshot(self, role: Role) -> dict:
        data = model_to_dict(role)
        data["permission_codes"] = sorted(permission.code for permission in role.permissions)
        data["user_count"] = sum(1 for link in role.user_links if not link.user.is_deleted)
        return data


role_service = RoleService()
