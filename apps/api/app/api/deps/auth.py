from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.db.session import get_db
from app.services.user import user_service

security = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: int
    username: str
    full_name: str
    email: str
    role_codes: list[str]
    permissions: list[str]


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not credentials:
        raise UnauthorizedException("Authentication is required.")
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
        raise UnauthorizedException("Access token is invalid.") from exc
    if payload.get("type") != "access":
        raise UnauthorizedException("Access token is invalid.")
    user = user_service.get_user_with_roles(db, int(payload["sub"]))
    if not user:
        raise UnauthorizedException("User not found.")
    auth_user = user_service.to_authenticated_user(user)
    return CurrentUser(
        id=auth_user.id,
        username=auth_user.username,
        full_name=auth_user.full_name,
        email=auth_user.email,
        role_codes=auth_user.roles,
        permissions=auth_user.permissions,
    )


def require_permissions(*permission_codes: str) -> Callable[[CurrentUser], CurrentUser]:
    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        missing = [code for code in permission_codes if code not in current_user.permissions]
        if missing:
            raise ForbiddenException("You do not have permission to perform this action.")
        return current_user

    return dependency
