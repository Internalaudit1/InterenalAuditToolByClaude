from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.base import BaseResponse


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    designation_id: int | None = None
    company_id: int | None = None
    location_id: int | None = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str
    role_codes: list[str]


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    phone: str | None = None
    designation_id: int | None = None
    company_id: int | None = None
    location_id: int | None = None
    is_active: bool | None = None


class UserRoleUpdate(BaseModel):
    role_codes: list[str]


class UserResponse(BaseResponse, UserBase):
    last_login_at: datetime | None = None
    role_codes: list[str] = []
    designation_title: str | None = None
    company_name: str | None = None
    location_label: str | None = None
