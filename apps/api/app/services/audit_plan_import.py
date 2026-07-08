from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction, AuditPlanApprovalStatus, CaroStatus, AuditScopeType, RiskRating
from app.core.exceptions import ValidationException
from app.models import Company, Location
from app.models.audit import AuditPlan
from app.schemas.imports import ImportCommitResponse, ImportRowError, ImportValidationResponse
from app.services.activity_log import activity_log_service
from app.services.excel_import import XLSX_MEDIA_TYPE

RESOURCE = "audit-plans"
MAX_ROWS = 2000

# Fixed upload format (compliance): headers must match exactly.
COL_SERIAL = "S. No."
COL_AREA = "Audit Area"
COL_NAME = "Audit Name"
COL_COMPANY = "Company"
COL_LOCATION = "Location"
COL_FY = "Fiscal Year"
COL_CRIT = "Criticality"
COL_CARO = "CARO/Non-CARO"
COL_SCOPE = "Internal/External"

TEMPLATE_HEADERS = [COL_SERIAL, COL_AREA, COL_NAME, COL_COMPANY, COL_LOCATION, COL_FY, COL_CRIT, COL_CARO, COL_SCOPE]
REQUIRED_HEADERS = {COL_AREA, COL_NAME, COL_COMPANY, COL_LOCATION, COL_FY}

CRITICALITY_VALUES = {v.value for v in RiskRating}
CARO_VALUES = {v.value for v in CaroStatus}
SCOPE_VALUES = {v.value for v in AuditScopeType}
FY_PATTERN = re.compile(r"^\d{4}-\d{4}$")


@dataclass
class ParsedRow:
    row_number: int
    values: dict[str, str]


class AuditPlanImportService:
    def template_filename(self) -> str:
        return "annual-audit-plan-template.xlsx"

    def error_report_filename(self) -> str:
        return "annual-audit-plan-errors.xlsx"

    # ---------- parsing ----------
    def _norm(self, value) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _read(self, content: bytes) -> list[ParsedRow]:
        try:
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        except Exception as exc:  # noqa: BLE001
            raise ValidationException("Unable to read the uploaded file. Please upload a valid .xlsx file.") from exc
        worksheet = workbook.active
        header_row_idx = None
        headers: list[str] = []
        for idx, row in enumerate(worksheet.iter_rows(min_row=1, max_row=15, values_only=True), start=1):
            cells = [self._norm(c) for c in row]
            if COL_AREA in cells and COL_NAME in cells:
                header_row_idx = idx
                headers = cells
                break
        if header_row_idx is None:
            raise ValidationException(
                "Header row not found. The file must contain the fixed columns: " + ", ".join(TEMPLATE_HEADERS)
            )
        missing = REQUIRED_HEADERS - set(headers)
        if missing:
            raise ValidationException("Missing required columns: " + ", ".join(sorted(missing)))
        index = {name: pos for pos, name in enumerate(headers)}
        rows: list[ParsedRow] = []
        for idx, row in enumerate(worksheet.iter_rows(min_row=header_row_idx + 1, values_only=True), start=header_row_idx + 1):
            cells = [self._norm(c) for c in row]
            record = {name: (cells[pos] if pos < len(cells) else "") for name, pos in index.items()}
            if not any(record.get(h) for h in REQUIRED_HEADERS):
                continue
            rows.append(ParsedRow(row_number=idx, values=record))
            if len(rows) >= MAX_ROWS:
                break
        return rows

    # ---------- validation ----------
    def _validate_row(self, db: Session, row: ParsedRow) -> tuple[dict | None, list[ImportRowError]]:
        errors: list[ImportRowError] = []
        v = row.values

        def require(col: str) -> str:
            value = v.get(col, "")
            if not value:
                errors.append(ImportRowError(row_number=row.row_number, field=col, value=None, message=f"{col} is required."))
            return value

        area = require(COL_AREA)
        name = require(COL_NAME)
        company_name = require(COL_COMPANY)
        location_name = require(COL_LOCATION)
        fiscal_year = require(COL_FY)

        if fiscal_year and not FY_PATTERN.match(fiscal_year):
            errors.append(ImportRowError(row_number=row.row_number, field=COL_FY, value=fiscal_year, message="Fiscal Year must look like 2026-2027."))

        company = None
        if company_name:
            company = db.scalar(select(Company).where(func.lower(Company.name) == company_name.lower(), Company.is_deleted.is_(False)))
            if not company:
                errors.append(ImportRowError(row_number=row.row_number, field=COL_COMPANY, value=company_name, message=f"Company '{company_name}' not found in masters."))

        location = None
        if location_name:
            stmt = select(Location).where(
                func.lower(Location.location_code) == location_name.lower(),
                Location.is_deleted.is_(False),
            )
            location = db.scalar(stmt)
            if not location:
                location = db.scalar(select(Location).where(func.lower(Location.description) == location_name.lower(), Location.is_deleted.is_(False)))
            if not location:
                errors.append(ImportRowError(row_number=row.row_number, field=COL_LOCATION, value=location_name, message=f"Location '{location_name}' not found (match by code or name)."))
            elif company and location.company_id != company.id:
                errors.append(ImportRowError(row_number=row.row_number, field=COL_LOCATION, value=location_name, message=f"Location '{location_name}' does not belong to company '{company_name}'."))

        criticality = v.get(COL_CRIT, "")
        if criticality and criticality not in CRITICALITY_VALUES:
            errors.append(ImportRowError(row_number=row.row_number, field=COL_CRIT, value=criticality, message=f"Criticality must be one of {sorted(CRITICALITY_VALUES)}."))
        caro = v.get(COL_CARO, "")
        if caro and caro not in CARO_VALUES:
            errors.append(ImportRowError(row_number=row.row_number, field=COL_CARO, value=caro, message=f"CARO/Non-CARO must be one of {sorted(CARO_VALUES)}."))
        scope = v.get(COL_SCOPE, "")
        if scope and scope not in SCOPE_VALUES:
            errors.append(ImportRowError(row_number=row.row_number, field=COL_SCOPE, value=scope, message=f"Internal/External must be one of {sorted(SCOPE_VALUES)}."))

        if errors:
            return None, errors

        serial_raw = v.get(COL_SERIAL, "")
        serial_no = int(serial_raw) if serial_raw.isdigit() else None
        record = {
            "audit_name": name,
            "audit_area": area,
            "company_id": company.id,
            "location_id": location.id,
            "fiscal_year": fiscal_year,
            "serial_no": serial_no,
            "criticality": criticality or None,
            "caro_status": caro or None,
            "audit_scope_type": scope or None,
            "planned_flag": True,
            "approval_status": AuditPlanApprovalStatus.DRAFT.value,
        }
        return record, []

    def _validate(self, db: Session, content: bytes) -> tuple[list[dict], list[ImportRowError], int]:
        rows = self._read(content)
        valid: list[dict] = []
        errors: list[ImportRowError] = []
        for row in rows:
            record, row_errors = self._validate_row(db, row)
            if record:
                valid.append(record)
            errors.extend(row_errors)
        return valid, errors, len(rows)

    def validate_workbook(self, db: Session, content: bytes) -> ImportValidationResponse:
        valid, errors, total = self._validate(db, content)
        invalid = total - len(valid)
        return ImportValidationResponse(
            resource=RESOURCE,
            total_rows=total,
            valid_rows=len(valid),
            invalid_rows=invalid,
            can_commit=total > 0 and invalid == 0,
            errors=errors,
        )

    def commit_workbook(self, db: Session, content: bytes, actor_name: str, actor_id: int | None) -> ImportCommitResponse:
        valid, errors, total = self._validate(db, content)
        invalid = total - len(valid)
        validation = ImportValidationResponse(
            resource=RESOURCE,
            total_rows=total,
            valid_rows=len(valid),
            invalid_rows=invalid,
            can_commit=total > 0 and invalid == 0,
            errors=errors,
        )
        if not validation.can_commit:
            return ImportCommitResponse(
                resource=RESOURCE,
                imported_rows=0,
                skipped_rows=total,
                message="Fix the highlighted rows before importing. No rows were saved.",
                validation=validation,
            )
        imported = 0
        for record in valid:
            record = {**record, "created_by": actor_name, "updated_by": actor_name, "created_by_user_id": actor_id, "updated_by_user_id": actor_id}
            db.add(AuditPlan(**record))
            imported += 1
        db.flush()
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="planning",
            entity_type="audit_plan",
            entity_id="bulk-import",
            action_type=ActivityAction.IMPORT.value,
            new_values={"imported_rows": imported},
        )
        return ImportCommitResponse(
            resource=RESOURCE,
            imported_rows=imported,
            skipped_rows=0,
            message=f"Imported {imported} audit plan rows as Draft. Approve them to lock.",
            validation=validation,
        )

    # ---------- template + error report ----------
    def generate_template(self) -> bytes:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Audit_Plan"
        header_fill = PatternFill("solid", fgColor="1F3864")
        required_fill = PatternFill("solid", fgColor="F97316")
        header_font = Font(bold=True, color="FFFFFF")
        for col_idx, header in enumerate(TEMPLATE_HEADERS, start=1):
            cell = worksheet.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = required_fill if header in REQUIRED_HEADERS else header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            worksheet.column_dimensions[cell.column_letter].width = max(16, min(len(header) + 6, 30))
        worksheet.freeze_panes = "A2"
        worksheet.append([1, "Procurement", "Procurement - North Plant", "NHL Limited", "002", "2026-2027", "High", "CARO", "Internal"])
        return self._to_bytes(workbook)

    def generate_error_report(self, db: Session, content: bytes) -> bytes:
        _, errors, _ = self._validate(db, content)
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Errors"
        for col_idx, header in enumerate(["Row", "Column", "Value", "Issue"], start=1):
            cell = worksheet.cell(row=1, column=col_idx, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="B91C1C")
        for err in errors:
            worksheet.append([err.row_number, err.field or "", "" if err.value is None else str(err.value), err.message])
        for column in "ABCD":
            worksheet.column_dimensions[column].width = 34
        return self._to_bytes(workbook)

    def _to_bytes(self, workbook: Workbook) -> bytes:
        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()


audit_plan_import_service = AuditPlanImportService()
