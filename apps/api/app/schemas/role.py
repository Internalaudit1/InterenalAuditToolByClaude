from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class PermissionResponse(BaseResponse):
    code: str
    description: str | None = None


class RoleCreate(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{1,49}$")
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class RolePermissionUpdate(BaseModel):
    permission_codes: list[str] = Field(default_factory=list)


class RoleResponse(BaseResponse):
    code: str
    name: str
    description: str | None = None
    is_system: bool
    permission_codes: list[str] = Field(default_factory=list)
    user_count: int = 0
