from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from starlette import status

from app.api.deps.auth import CurrentUser, require_permissions
from app.db.session import get_db
from app.schemas.imports import ImportValidationResponse
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
