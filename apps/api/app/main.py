from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.action_plans import router as action_plans_router
from app.api.routes.admin import router as admin_router
from app.api.routes.audits import router as audits_router
from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.imports import router as imports_router
from app.api.routes.knowledge_library import router as library_router
from app.api.routes.master_data import router as master_router
from app.api.routes.meta import router as meta_router
from app.api.routes.planning import router as planning_router
from app.api.routes.reports import router as reports_router
from app.core.config import settings
from app.db.session import verify_runtime_database
from app.middleware.error_handler import add_exception_handlers
from app.middleware.request_context import RequestContextMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    verify_runtime_database()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID", "X-Response-Time-Ms"],
)
add_exception_handlers(app)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(planning_router)
api_router.include_router(audits_router)
api_router.include_router(action_plans_router)
api_router.include_router(reports_router)
api_router.include_router(library_router)
api_router.include_router(master_router)
api_router.include_router(imports_router)
api_router.include_router(admin_router)
api_router.include_router(meta_router)
app.include_router(api_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
