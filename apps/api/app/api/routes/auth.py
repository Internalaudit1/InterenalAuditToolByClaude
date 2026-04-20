from __future__ import annotations

from collections import defaultdict, deque
from time import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.common import MessageResponse
from app.services.user import user_service

router = APIRouter(prefix="/auth", tags=["auth"])
login_attempts: dict[str, deque[float]] = defaultdict(deque)


def _check_rate_limit(ip_address: str | None) -> None:
    if not ip_address:
        return
    bucket = login_attempts[ip_address]
    now = time()
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= 20:
        raise ValidationException("Too many login attempts. Please retry after one minute.")
    bucket.append(now)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    _check_rate_limit(getattr(request.state, "ip_address", None))
    return user_service.authenticate(
        db,
        username=payload.username,
        password=payload.password,
        request_meta={
            "path": str(request.url.path),
            "method": request.method,
            "ip_address": getattr(request.state, "ip_address", None),
            "user_agent": getattr(request.state, "user_agent", None),
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return user_service.refresh(db, payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout() -> MessageResponse:
    return MessageResponse(message="Client-side token removal required for logout in this demo.")
