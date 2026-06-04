from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "AuthenticatedUser"


class AuthenticatedUser(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    company_id: int | None = None
    location_id: int | None = None
    roles: list[str]
    permissions: list[str]
    last_login_at: datetime | None = None


class LoginAuditResponse(BaseModel):
    success: bool
    user: AuthenticatedUser
