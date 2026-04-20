from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, get_current_user, require_permissions
from app.api.deps.common import get_list_query
from app.core.exceptions import ForbiddenException
from app.db.session import get_db
from app.models.support import ActivityLog, Notification
from app.schemas.common import BulkDeleteRequest, BulkDeleteResponse, ListQuery, MessageResponse
from app.schemas.role import PermissionResponse, RoleCreate, RolePermissionUpdate, RoleResponse, RoleUpdate
from app.schemas.user import UserCreate, UserResponse, UserRoleUpdate, UserUpdate
from app.services.role import role_service
from app.services.user import user_service
from app.utils.serialization import model_to_dict

router = APIRouter(prefix="/admin", tags=["admin"])


def _role_response(role) -> RoleResponse:
    return RoleResponse(
        **{
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "description": role.description,
            "is_system": role.is_system,
            "permission_codes": sorted(permission.code for permission in role.permissions),
            "user_count": sum(1 for link in role.user_links if not link.user.is_deleted),
            "created_at": role.created_at,
            "updated_at": role.updated_at,
            "created_by": role.created_by,
            "updated_by": role.updated_by,
            "is_deleted": role.is_deleted,
        }
    )


def _permission_response(permission) -> PermissionResponse:
    return PermissionResponse(
        **{
            "id": permission.id,
            "code": permission.code,
            "description": permission.description,
            "created_at": permission.created_at,
            "updated_at": permission.updated_at,
            "created_by": permission.created_by,
            "updated_by": permission.updated_by,
            "is_deleted": permission.is_deleted,
        }
    )


@router.get("/activity-logs")
def list_activity_logs(
    query: Annotated[ListQuery, Depends(get_list_query)],
    _: CurrentUser = Depends(require_permissions("activity_logs:view")),
    db: Session = Depends(get_db),
):
    stmt = select(ActivityLog).where(ActivityLog.is_deleted.is_(False)).order_by(ActivityLog.created_at.desc())
    logs = list(db.scalars(stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)).all())
    return {"items": [model_to_dict(log) for log in logs], "page": query.page, "page_size": query.page_size}


@router.get("/notifications")
def list_notifications(
    current_user: CurrentUser = Depends(require_permissions("notifications:view")),
    db: Session = Depends(get_db),
):
    stmt = select(Notification).where(Notification.user_id == current_user.id, Notification.is_deleted.is_(False)).order_by(Notification.created_at.desc())
    return [model_to_dict(notification) for notification in db.scalars(stmt).all()]


@router.get("/users", response_model=list[UserResponse])
def list_users(
    _: CurrentUser = Depends(require_permissions("users:view")),
    db: Session = Depends(get_db),
):
    users = user_service.list_users(db)
    return [
        UserResponse(
            **{
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "designation_id": user.designation_id,
                "company_id": user.company_id,
                "location_id": user.location_id,
                "is_active": user.is_active,
                "last_login_at": user.last_login_at,
                "role_codes": [link.role.code for link in user.role_links],
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "created_by": user.created_by,
                "updated_by": user.updated_by,
                "is_deleted": user.is_deleted,
            }
        )
        for user in users
    ]


@router.post("/users", response_model=UserResponse)
def create_user(
    payload: UserCreate,
    current_user: CurrentUser = Depends(require_permissions("users:manage")),
    db: Session = Depends(get_db),
):
    user = user_service.create_user(db, payload, current_user.full_name, current_user.role_codes)
    db.commit()
    db.refresh(user)
    return UserResponse(
        **{
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "designation_id": user.designation_id,
            "company_id": user.company_id,
            "location_id": user.location_id,
            "is_active": user.is_active,
            "last_login_at": user.last_login_at,
            "role_codes": [link.role.code for link in user.role_links],
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "created_by": user.created_by,
            "updated_by": user.updated_by,
            "is_deleted": user.is_deleted,
        }
    )


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: CurrentUser = Depends(require_permissions("users:manage")),
    db: Session = Depends(get_db),
):
    user = user_service.update_user(db, user_id, payload, current_user.full_name)
    db.commit()
    db.refresh(user)
    return UserResponse(
        **{
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "designation_id": user.designation_id,
            "company_id": user.company_id,
            "location_id": user.location_id,
            "is_active": user.is_active,
            "last_login_at": user.last_login_at,
            "role_codes": [link.role.code for link in user.role_links],
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "created_by": user.created_by,
            "updated_by": user.updated_by,
            "is_deleted": user.is_deleted,
        }
    )


@router.put("/users/{user_id}/roles", response_model=UserResponse)
def update_user_roles(
    user_id: int,
    payload: UserRoleUpdate,
    current_user: CurrentUser = Depends(require_permissions("users:manage")),
    db: Session = Depends(get_db),
):
    user = user_service.update_roles(db, user_id, payload.role_codes, current_user.full_name, current_user.role_codes, current_user.id)
    db.commit()
    db.refresh(user)
    return UserResponse(
        **{
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "designation_id": user.designation_id,
            "company_id": user.company_id,
            "location_id": user.location_id,
            "is_active": user.is_active,
            "last_login_at": user.last_login_at,
            "role_codes": [link.role.code for link in user.role_links],
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "created_by": user.created_by,
            "updated_by": user.updated_by,
            "is_deleted": user.is_deleted,
        }
    )


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(
    _: CurrentUser = Depends(require_permissions("roles:view")),
    db: Session = Depends(get_db),
):
    return [_permission_response(permission) for permission in role_service.list_permissions(db)]


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if "roles:view" not in current_user.permissions and "users:manage" not in current_user.permissions:
        raise ForbiddenException("You do not have permission to view roles.")
    return [_role_response(role) for role in role_service.list_roles(db, actor_role_codes=current_user.role_codes)]


@router.post("/roles", response_model=RoleResponse)
def create_role(
    payload: RoleCreate,
    current_user: CurrentUser = Depends(require_permissions("roles:manage")),
    db: Session = Depends(get_db),
):
    role = role_service.create_role(db, payload, current_user.full_name, current_user.id)
    db.commit()
    db.refresh(role)
    return _role_response(role_service.get_role(db, role.id))


@router.put("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    current_user: CurrentUser = Depends(require_permissions("roles:manage")),
    db: Session = Depends(get_db),
):
    role = role_service.update_role(db, role_id, payload, current_user.full_name, current_user.id)
    db.commit()
    return _role_response(role_service.get_role(db, role.id))


@router.put("/roles/{role_id}/permissions", response_model=RoleResponse)
def update_role_permissions(
    role_id: int,
    payload: RolePermissionUpdate,
    current_user: CurrentUser = Depends(require_permissions("roles:manage")),
    db: Session = Depends(get_db),
):
    role = role_service.update_permissions(db, role_id, payload, current_user.full_name, current_user.id)
    db.commit()
    return _role_response(role_service.get_role(db, role.id))


@router.delete("/roles/{role_id}", response_model=MessageResponse)
def delete_role(
    role_id: int,
    current_user: CurrentUser = Depends(require_permissions("roles:manage")),
    db: Session = Depends(get_db),
):
    role_service.delete_role(db, role_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="Role deleted.")


@router.delete("/users/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: int,
    current_user: CurrentUser = Depends(require_permissions("users:delete")),
    db: Session = Depends(get_db),
):
    user_service.delete_user(db, user_id, current_user.full_name, current_user.id)
    db.commit()
    return MessageResponse(message="User deleted.")


@router.post("/users/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_users(
    payload: BulkDeleteRequest,
    current_user: CurrentUser = Depends(require_permissions("users:delete")),
    db: Session = Depends(get_db),
):
    response = user_service.bulk_delete_users(db, payload.ids, current_user.full_name, current_user.id)
    db.commit()
    return response
