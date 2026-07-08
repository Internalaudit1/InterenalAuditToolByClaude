from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from starlette import status

from app.api.deps.auth import CurrentUser, require_permissions
from app.db.session import get_db
from app.schemas.imports import AuditUniverseValidationResponse, ImportCommitResponse, ImportValidationResponse
from app.services.audit_plan_import import audit_plan_import_service
from app.services.audit_universe_import import audit_universe_import_service
from app.services.excel_import import XLSX_MEDIA_TYPE, master_excel_import_service

router = APIRouter(prefix="/imports", tags=["imports"])


def _download_response(content: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(content),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/master/{resource}/template")
def download_master_import_template(
    resource: str,
    _: CurrentUser = Depends(require_permissions("masters:manage")),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    content = master_excel_import_service.generate_template(db, resource)
    return _download_response(content, master_excel_import_service.template_filename(resource))


@router.post("/master/{resource}/validate", response_model=ImportValidationResponse)
async def validate_master_import(
    resource: str,
    file: UploadFile = File(...),
    _: CurrentUser = Depends(require_permissions("masters:manage")),
    db: Session = Depends(get_db),
) -> ImportValidationResponse:
    content = await file.read()
    return master_excel_import_service.validate_workbook(db, resource, content, file.filename).summary


@router.post("/master/{resource}/commit", response_model=None)
async def commit_master_import(
    resource: str,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permissions("masters:manage")),
    db: Session = Depends(get_db),
):
    content = await file.read()
    response = master_excel_import_service.commit_workbook(db, resource, content, file.filename, current_user.full_name, current_user.id)
    if not response.validation.can_commit:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=jsonable_encoder(response))
    db.commit()
    return response


@router.post("/master/{resource}/error-report")
async def download_master_import_error_report(
    resource: str,
    file: UploadFile = File(...),
    _: CurrentUser = Depends(require_permissions("masters:manage")),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    content = await file.read()
    report = master_excel_import_service.generate_error_report(db, resource, content, file.filename)
    return _download_response(report, master_excel_import_service.error_report_filename(resource))


@router.get("/audit-universe/template")
def download_audit_universe_template(
    _: CurrentUser = Depends(require_permissions("masters:manage")),
) -> StreamingResponse:
    content = audit_universe_import_service.generate_template()
    return _download_response(content, audit_universe_import_service.template_filename())


@router.post("/audit-universe/validate", response_model=AuditUniverseValidationResponse)
async def validate_audit_universe_import(
    file: UploadFile = File(...),
    _: CurrentUser = Depends(require_permissions("masters:manage")),
    db: Session = Depends(get_db),
) -> AuditUniverseValidationResponse:
    content = await file.read()
    return audit_universe_import_service.validate_workbook(db, content, file.filename)


@router.post("/audit-universe/commit", response_model=None)
async def commit_audit_universe_import(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permissions("masters:manage")),
    db: Session = Depends(get_db),
):
    content = await file.read()
    response = audit_universe_import_service.commit_workbook(db, content, file.filename, current_user.full_name, current_user.id)
    if not response.validation.can_commit:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=jsonable_encoder(response))
    db.commit()
    return response


@router.post("/audit-universe/error-report")
async def download_audit_universe_error_report(
    file: UploadFile = File(...),
    _: CurrentUser = Depends(require_permissions("masters:manage")),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    content = await file.read()
    report = audit_universe_import_service.generate_error_report(db, content, file.filename)
    return _download_response(report, audit_universe_import_service.error_report_filename())


@router.get("/audit-plans/template")
def download_audit_plan_template(
    _: CurrentUser = Depends(require_permissions("planning:manage")),
) -> StreamingResponse:
    content = audit_plan_import_service.generate_template()
    return _download_response(content, audit_plan_import_service.template_filename())


@router.post("/audit-plans/validate", response_model=ImportValidationResponse)
async def validate_audit_plan_import(
    file: UploadFile = File(...),
    _: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
) -> ImportValidationResponse:
    content = await file.read()
    return audit_plan_import_service.validate_workbook(db, content)


@router.post("/audit-plans/commit", response_model=None)
async def commit_audit_plan_import(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    content = await file.read()
    response = audit_plan_import_service.commit_workbook(db, content, current_user.full_name, current_user.id)
    if not response.validation.can_commit:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=jsonable_encoder(response))
    db.commit()
    return response


@router.post("/audit-plans/error-report")
async def download_audit_plan_error_report(
    file: UploadFile = File(...),
    _: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    content = await file.read()
    report = audit_plan_import_service.generate_error_report(db, content)
    return _download_response(report, audit_plan_import_service.error_report_filename())


@router.post("/audit-plans/legacy/validate", response_model=ImportValidationResponse)
async def validate_legacy_audit_plan_import(
    company_id: int = Form(...),
    location_id: int = Form(...),
    fiscal_year: str = Form(...),
    file: UploadFile = File(...),
    _: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
) -> ImportValidationResponse:
    content = await file.read()
    return audit_plan_import_service.validate_legacy_workbook(db, content, company_id, location_id, fiscal_year)


@router.post("/audit-plans/legacy/commit", response_model=None)
async def commit_legacy_audit_plan_import(
    company_id: int = Form(...),
    location_id: int = Form(...),
    fiscal_year: str = Form(...),
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permissions("planning:manage")),
    db: Session = Depends(get_db),
):
    content = await file.read()
    response = audit_plan_import_service.commit_legacy_workbook(db, content, company_id, location_id, fiscal_year, current_user.full_name, current_user.id)
    if not response.validation.can_commit:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=jsonable_encoder(response))
    db.commit()
    return response
