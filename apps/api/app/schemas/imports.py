from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ImportRowError(BaseModel):
    row_number: int
    field: str | None = None
    value: Any | None = None
    message: str


class ImportValidationResponse(BaseModel):
    resource: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    can_commit: bool
    errors: list[ImportRowError]


class ImportCommitResponse(BaseModel):
    resource: str
    imported_rows: int
    skipped_rows: int
    message: str
    validation: ImportValidationResponse
