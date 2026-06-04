from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import ActivityAction, RoleCode
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, UnauthorizedException, ValidationException
from app.core.permissions import PERMISSIONS_BY_ROLE
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.action_plan import ActionPlan
from app.models.audit import Audit, AuditPlan, BusinessInitiative
from app.models.auth import Permission, RefreshToken, Role, User, UserRole
from app.models.master import Auditee
from app.models.support import Notification
from app.repositories.base import BaseRepository
from app.schemas.auth import AuthenticatedUser, TokenResponse
from app.schemas.common import BlockedDeleteItem, BulkDeleteResponse
from app.schemas.user import UserCreate, UserUpdate
from app.services.activity_log import activity_log_service
from app.utils.serialization import model_to_dict


class UserService:
    user_repo = BaseRepository(User)
    refresh_token_repo = BaseRepository(RefreshToken)
    notification_repo = BaseRepository(Notification)

    def get_user_with_roles(self, db: Session, user_id: int) -> User | None:
        stmt = (
            select(User)
            .options(joinedload(User.role_links).joinedload(UserRole.role).joinedload(Role.permissions))
            .where(User.id == user_id, User.is_deleted.is_(False))
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    def get_by_username(self, db: Session, username: str) -> User | None:
        stmt = (
            select(User)
            .options(joinedload(User.role_links).joinedload(UserRole.role).joinedload(Role.permissions))
            .where(User.username == username, User.is_deleted.is_(False))
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    def _base_user_stmt(self):
        return (
            select(User)
            .options(
                joinedload(User.role_links).joinedload(UserRole.role),
                joinedload(User.designation),
                joinedload(User.company),
                joinedload(User.location),
            )
            .where(User.is_deleted.is_(False))
        )

    def list_users(
        self,
        db: Session,
        *,
        q: str | None = None,
        role: str | None = None,
        roles: list[str] | None = None,
        active_only: bool = False,
        company_id: int | None = None,
        location_id: int | None = None,
        page_size: int | None = None,
    ) -> list[User]:
        stmt = self._base_user_stmt()
        if active_only:
            stmt = stmt.where(User.is_active.is_(True))
        if company_id:
            stmt = stmt.where(User.company_id == company_id)
        if location_id:
            stmt = stmt.where(User.location_id == location_id)
        role_codes = [code for code in [role, *(roles or [])] if code]
        if role_codes:
            stmt = stmt.join(User.role_links).join(UserRole.role).where(Role.code.in_(role_codes), Role.is_deleted.is_(False))
        if q:
            stmt = stmt.where(
                or_(
                    User.full_name.ilike(f"%{q}%"),
                    User.username.ilike(f"%{q}%"),
                    User.email.ilike(f"%{q}%"),
                    User.phone.ilike(f"%{q}%"),
                )
            )
        stmt = stmt.order_by(User.full_name.asc(), User.username.asc())
        if page_size:
            stmt = stmt.limit(page_size)
        return list(db.execute(stmt).unique().scalars().all())

    def to_authenticated_user(self, user: User) -> AuthenticatedUser:
        roles = [link.role.code for link in user.role_links]
        permissions = sorted({permission.code for link in user.role_links for permission in link.role.permissions})
        return AuthenticatedUser(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            company_id=user.company_id,
            location_id=user.location_id,
            roles=roles,
            permissions=permissions,
            last_login_at=user.last_login_at,
        )

    def authenticate(
        self,
        db: Session,
        *,
        username: str,
        password: str,
        request_meta: dict[str, str | None],
    ) -> TokenResponse:
        user = self.get_by_username(db, username)
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid username or password.")
        if not user.is_active:
            raise ForbiddenException("User account is inactive.")

        user.last_login_at = datetime.now(UTC)
        roles = [link.role.code for link in user.role_links]
        access_token = create_access_token(str(user.id), {"roles": roles})
        refresh_token = create_refresh_token(str(user.id))
        refresh_record = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(days=7),
            created_by=user.username,
            updated_by=user.username,
        )
        db.add(refresh_record)
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=user.id,
            actor_name=user.full_name,
            role=",".join(roles),
            module="auth",
            entity_type="user",
            entity_id=str(user.id),
            action_type=ActivityAction.LOGIN.value,
            new_values={"username": user.username},
            request_path=request_meta.get("path"),
            request_method=request_meta.get("method"),
            ip_address=request_meta.get("ip_address"),
            user_agent=request_meta.get("user_agent"),
            correlation_id=request_meta.get("correlation_id"),
        )
        db.commit()
        db.refresh(user)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
            user=self.to_authenticated_user(user),
        )

    def refresh(self, db: Session, refresh_token: str) -> TokenResponse:
        token_record = db.scalar(select(RefreshToken).where(RefreshToken.token == refresh_token, RefreshToken.revoked_at.is_(None)))
        if not token_record:
            raise UnauthorizedException("Refresh token is invalid or expired.")
        user = self.get_user_with_roles(db, token_record.user_id)
        if not user:
            raise UnauthorizedException("User no longer exists.")
        roles = [link.role.code for link in user.role_links]
        return TokenResponse(
            access_token=create_access_token(str(user.id), {"roles": roles}),
            refresh_token=refresh_token,
            expires_in=3600,
            user=self.to_authenticated_user(user),
        )

    def ensure_roles_seeded(self, db: Session) -> None:
        existing = {role.code: role for role in db.scalars(select(Role)).all()}
        permissions_by_code = {permission.code: permission for permission in db.scalars(select(Permission)).all()}
        for permission_codes in PERMISSIONS_BY_ROLE.values():
            for code in permission_codes:
                if code not in permissions_by_code:
                    permission = Permission(code=code, description=code.replace(":", " ").title(), created_by="seed", updated_by="seed")
                    db.add(permission)
                    db.flush()
                    permissions_by_code[code] = permission
        for role_code, permission_codes in PERMISSIONS_BY_ROLE.items():
            role = existing.get(role_code.value)
            if not role:
                role = Role(code=role_code.value, name=role_code.name.replace("_", " ").title(), is_system=True, created_by="seed", updated_by="seed")
                db.add(role)
                db.flush()
                existing[role_code.value] = role
            role.is_system = True
            role.permissions = [permissions_by_code[code] for code in sorted(permission_codes)]
        db.flush()

    def create_user(self, db: Session, payload: UserCreate, actor_name: str, actor_role_codes: list[str] | None = None) -> User:
        if self.get_by_username(db, payload.username):
            raise ValidationException("Username already exists.")
        self._ensure_actor_can_assign_roles(payload.role_codes, actor_role_codes)
        roles = list(db.scalars(select(Role).where(Role.code.in_(payload.role_codes), Role.is_deleted.is_(False))).all())
        if len(roles) != len(payload.role_codes):
            raise ValidationException("One or more roles are invalid.")
        user = User(
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            phone=payload.phone,
            designation_id=payload.designation_id,
            company_id=payload.company_id,
            location_id=payload.location_id,
            is_active=payload.is_active,
            created_by=actor_name,
            updated_by=actor_name,
        )
        db.add(user)
        db.flush()
        user.role_links = [UserRole(user_id=user.id, role_id=role.id) for role in roles]
        db.flush()
        return user

    def update_user(self, db: Session, user_id: int, payload: UserUpdate, actor_name: str) -> User:
        user = self.get_user_with_roles(db, user_id)
        if not user:
            raise NotFoundException("User not found.")
        before = model_to_dict(user)
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(user, field, value)
        user.updated_by = actor_name
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=user.id,
            actor_name=actor_name,
            role=None,
            module="admin",
            entity_type="user",
            entity_id=str(user.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=model_to_dict(user),
        )
        return user

    def update_roles(self, db: Session, user_id: int, role_codes: list[str], actor_name: str, actor_role_codes: list[str] | None = None, actor_id: int | None = None) -> User:
        user = self.get_user_with_roles(db, user_id)
        if not user:
            raise NotFoundException("User not found.")
        self._ensure_actor_can_assign_roles(role_codes, actor_role_codes)
        roles = list(db.scalars(select(Role).where(Role.code.in_(role_codes), Role.is_deleted.is_(False))).all())
        if len(roles) != len(role_codes):
            raise ValidationException("One or more roles are invalid.")
        before = {"role_codes": [link.role.code for link in user.role_links]}
        user.role_links = [UserRole(user_id=user.id, role_id=role.id) for role in roles]
        user.updated_by = actor_name
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="admin",
            entity_type="user_roles",
            entity_id=str(user.id),
            action_type=ActivityAction.ASSIGN.value,
            old_values=before,
            new_values={"role_codes": role_codes},
        )
        return user

    def _ensure_actor_can_assign_roles(self, role_codes: list[str], actor_role_codes: list[str] | None) -> None:
        if actor_role_codes is None:
            return
        if RoleCode.SUPER_ADMIN.value in role_codes and RoleCode.SUPER_ADMIN.value not in actor_role_codes:
            raise ForbiddenException("Only Super Admin can assign the Super Admin role.")

    def _ensure_user_can_be_deleted(self, db: Session, user_id: int) -> None:
        dependency_checks: list[tuple[type, str, str]] = [
            (AuditPlan, "audit_owner_id", "active audit plans"),
            (Audit, "audit_owner_id", "active audits"),
            (ActionPlan, "implementation_owner_user_id", "active action plans as implementation owner"),
            (ActionPlan, "assigned_auditor_user_id", "active action plans as assigned auditor"),
            (BusinessInitiative, "owner_user_id", "active business initiatives"),
            (Auditee, "linked_user_id", "active auditee master records"),
        ]
        for model, field_name, label in dependency_checks:
            dependent_id = db.scalar(select(model.id).where(getattr(model, field_name) == user_id, model.is_deleted.is_(False)).limit(1))
            if dependent_id:
                raise ConflictException(f"This user cannot be deleted because they are still assigned to {label}.")

    def delete_user(self, db: Session, user_id: int, actor_name: str, actor_id: int | None) -> None:
        user = self.get_user_with_roles(db, user_id)
        if not user:
            raise NotFoundException("User not found.")
        self._ensure_user_can_be_deleted(db, user_id)
        before = model_to_dict(user)

        for refresh_token in user.refresh_tokens:
            if refresh_token.is_deleted:
                continue
            refresh_token.revoked_at = datetime.now(UTC)
            self.refresh_token_repo.soft_delete(db, refresh_token, actor_name=actor_name)

        for notification in user.notifications:
            if notification.is_deleted:
                continue
            self.notification_repo.soft_delete(db, notification, actor_name=actor_name)

        user.is_active = False
        self.user_repo.soft_delete(db, user, actor_name=actor_name)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="admin",
            entity_type="user",
            entity_id=str(user.id),
            action_type=ActivityAction.DELETE.value,
            old_values=before,
            new_values={"is_deleted": True, "is_active": False},
        )

    def bulk_delete_users(self, db: Session, ids: list[int], actor_name: str, actor_id: int | None) -> BulkDeleteResponse:
        deleted_ids: list[int] = []
        blocked: list[BlockedDeleteItem] = []
        for user_id in ids:
            try:
                self.delete_user(db, user_id, actor_name, actor_id)
                deleted_ids.append(user_id)
            except (ConflictException, NotFoundException) as exc:
                blocked.append(BlockedDeleteItem(id=user_id, reason=str(exc.detail)))
        response = BulkDeleteResponse(
            deleted_ids=deleted_ids,
            blocked=blocked,
            message=(
                f"Deleted {len(deleted_ids)} record(s)." if deleted_ids and not blocked else
                f"Deleted {len(deleted_ids)} record(s); {len(blocked)} record(s) were blocked by dependencies." if deleted_ids else
                "No records were deleted."
            ),
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="admin",
            entity_type="user",
            entity_id="bulk",
            action_type=ActivityAction.DELETE.value,
            new_values=response.model_dump(),
        )
        return response


user_service = UserService()
