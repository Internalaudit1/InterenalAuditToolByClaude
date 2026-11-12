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


class AuditUniverseCandidate(BaseModel):
    kind: str
    action: str
    name: str
    code: str | None = None
    company_name: str | None = None
    location_name: str | None = None
    process_name: str | None = None
    row_count: int = 0
    source_values: list[str] = []


class AuditUniverseValidationResponse(BaseModel):
    resource: str = "audit-universe"
    total_rows: int
    usable_rows: int
    unresolved_rows: int
    can_commit: bool
    summary: dict[str, int]
    candidates: list[AuditUniverseCandidate]
    unresolved: list[ImportRowError]
    warnings: list[str] = []


class AuditUniverseCommitResponse(BaseModel):
    resource: str = "audit-universe"
    created: dict[str, int]
    reused: dict[str, int]
    skipped_rows: int
    message: str
    validation: AuditUniverseValidationResponse
