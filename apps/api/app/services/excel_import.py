from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction
from app.core.exceptions import NotFoundException
from app.core.permissions import MASTER_RESOURCE_MAP
from app.schemas.imports import ImportCommitResponse, ImportRowError, ImportValidationResponse
from app.schemas.master import MasterRecordCreate
from app.services.activity_log import activity_log_service
from app.services.import_specs import ImportColumnSpec, MasterImportSpec, PHASE_ONE_MASTER_IMPORT_SPECS
from app.services.master import master_service

MAX_IMPORT_ROWS = 1000
DATA_ENTRY_SHEET = "Data_Entry"
INSTRUCTIONS_SHEET = "Instructions"
REFERENCE_VALUES_SHEET = "Reference_Values"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass
class ParsedRow:
    row_number: int
    raw_values: dict[str, Any]
    data: dict[str, Any]
    errors: list[ImportRowError]


@dataclass
class ValidationResult:
    summary: ImportValidationResponse
    rows: list[ParsedRow]


class MasterExcelImportService:
    def get_spec(self, resource: str) -> MasterImportSpec:
        spec = PHASE_ONE_MASTER_IMPORT_SPECS.get(resource)
        if not spec:
            raise NotFoundException(f"Master import is not supported for resource '{resource}'.")
        return spec

    def template_filename(self, resource: str) -> str:
        spec = self.get_spec(resource)
        return f"{spec.resource}-import-template.xlsx"

    def error_report_filename(self, resource: str) -> str:
        spec = self.get_spec(resource)
        return f"{spec.resource}-import-errors.xlsx"

    def generate_template(self, db: Session, resource: str) -> bytes:
        spec = self.get_spec(resource)
        workbook = Workbook()
        data_sheet = workbook.active
        data_sheet.title = DATA_ENTRY_SHEET
        instructions_sheet = workbook.create_sheet(INSTRUCTIONS_SHEET)

        self._build_data_entry_sheet(data_sheet, spec)
        self._build_instructions_sheet(instructions_sheet, spec)
        if any(column.lookup for column in spec.columns):
            reference_sheet = workbook.create_sheet(REFERENCE_VALUES_SHEET)
            self._build_reference_sheet(db, reference_sheet, spec)

        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def validate_workbook(self, db: Session, resource: str, file_bytes: bytes, filename: str | None) -> ValidationResult:
        spec = self.get_spec(resource)
        file_errors = self._validate_file(filename)
        if file_errors:
            return self._build_result(spec, [], file_errors)

        try:
            workbook = load_workbook(BytesIO(file_bytes), data_only=True)
        except Exception as exc:
            error = ImportRowError(row_number=0, field=None, value=None, message=f"Unable to read workbook: {exc}")
            return self._build_result(spec, [], [error])

        if DATA_ENTRY_SHEET not in workbook.sheetnames:
            error = ImportRowError(row_number=0, field=None, value=None, message=f"Required sheet '{DATA_ENTRY_SHEET}' is missing.")
            return self._build_result(spec, [], [error])

        worksheet = workbook[DATA_ENTRY_SHEET]
        header_errors = self._validate_headers(worksheet, spec)
        if header_errors:
            return self._build_result(spec, [], header_errors)

        rows = self._parse_rows(db, worksheet, spec)
        file_level_errors: list[ImportRowError] = []
        if not rows:
            file_level_errors.append(ImportRowError(row_number=0, field=None, value=None, message="Workbook contains no data rows."))
        if len(rows) > MAX_IMPORT_ROWS:
            file_level_errors.append(
                ImportRowError(
                    row_number=0,
                    field=None,
                    value=len(rows),
                    message=f"Workbook contains {len(rows)} rows. The Phase 1 limit is {MAX_IMPORT_ROWS} rows per import.",
                )
            )

        self._apply_duplicate_checks(db, spec, rows)
        return self._build_result(spec, rows, file_level_errors)

    def commit_workbook(
        self,
        db: Session,
        resource: str,
        file_bytes: bytes,
        filename: str | None,
        actor_name: str,
        actor_id: int | None,
    ) -> ImportCommitResponse:
        validation = self.validate_workbook(db, resource, file_bytes, filename)
        if not validation.summary.can_commit:
            return ImportCommitResponse(
                resource=resource,
                imported_rows=0,
                skipped_rows=validation.summary.total_rows,
                message="Import was not committed because validation failed.",
                validation=validation.summary,
            )

        imported = 0
        for row in validation.rows:
            payload = MasterRecordCreate(**row.data)
            master_service.create(db, resource, payload, actor_name, actor_id)
            imported += 1

        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="master_import",
            entity_type=MASTER_RESOURCE_MAP[resource],
            entity_id="bulk",
            action_type=ActivityAction.IMPORT.value,
            new_values={"resource": resource, "imported_rows": imported, "mode": "strict_insert_only"},
        )
        return ImportCommitResponse(
            resource=resource,
            imported_rows=imported,
            skipped_rows=0,
            message=f"Imported {imported} {self.get_spec(resource).display_name.lower()} record(s).",
            validation=validation.summary,
        )

    def generate_error_report(self, db: Session, resource: str, file_bytes: bytes, filename: str | None) -> bytes:
        spec = self.get_spec(resource)
        validation = self.validate_workbook(db, resource, file_bytes, filename)
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Import_Errors"

        headers = [*spec.expected_headers, "error_fields", "error_messages"]
        for column_index, header in enumerate(headers, start=1):
            cell = worksheet.cell(row=1, column=column_index, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="B91C1C")

        invalid_rows = [row for row in validation.rows if row.errors]
        if invalid_rows:
            for output_row, row in enumerate(invalid_rows, start=2):
                for column_index, header in enumerate(spec.expected_headers, start=1):
                    worksheet.cell(row=output_row, column=column_index, value=row.raw_values.get(header))
                worksheet.cell(row=output_row, column=len(spec.expected_headers) + 1, value=", ".join(sorted({error.field or "file" for error in row.errors})))
                worksheet.cell(row=output_row, column=len(spec.expected_headers) + 2, value=" | ".join(error.message for error in row.errors))
        else:
            for output_row, error in enumerate(validation.summary.errors, start=2):
                worksheet.cell(row=output_row, column=len(spec.expected_headers) + 1, value=error.field or "file")
                worksheet.cell(row=output_row, column=len(spec.expected_headers) + 2, value=error.message)

        for column in worksheet.columns:
            width = min(max(len(str(cell.value or "")) for cell in column) + 2, 60)
            worksheet.column_dimensions[column[0].column_letter].width = width

        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def _validate_file(self, filename: str | None) -> list[ImportRowError]:
        if not filename or not filename.lower().endswith(".xlsx"):
            return [ImportRowError(row_number=0, field=None, value=filename, message="Only .xlsx files are supported for Phase 1 master import.")]
        return []

    def _validate_headers(self, worksheet: Any, spec: MasterImportSpec) -> list[ImportRowError]:
        raw_headers = [cell.value for cell in worksheet[1]]
        headers = [str(value).strip() for value in raw_headers if self._has_value(value)]
        expected = spec.expected_headers
        if headers == expected:
            return []

        errors: list[ImportRowError] = []
        missing = [header for header in expected if header not in headers]
        extra = [header for header in headers if header not in expected]
        if missing:
            errors.append(ImportRowError(row_number=1, field=None, value=", ".join(missing), message="Missing required header(s)."))
        if extra:
            errors.append(ImportRowError(row_number=1, field=None, value=", ".join(extra), message="Unexpected header(s) found."))
        if not missing and not extra:
            errors.append(ImportRowError(row_number=1, field=None, value=", ".join(headers), message="Headers must appear in the same order as the downloaded template."))
        return errors

    def _parse_rows(self, db: Session, worksheet: Any, spec: MasterImportSpec) -> list[ParsedRow]:
        rows: list[ParsedRow] = []
        headers = spec.expected_headers
        for row_number in range(2, worksheet.max_row + 1):
            raw_values = {header: worksheet.cell(row=row_number, column=index).value for index, header in enumerate(headers, start=1)}
            if not any(self._has_value(value) for value in raw_values.values()):
                continue
            parsed = ParsedRow(row_number=row_number, raw_values=raw_values, data={}, errors=[])
            for column in spec.columns:
                raw_value = raw_values.get(column.header)
                value = self._coerce_value(column, raw_value, parsed.errors, row_number)
                if parsed.errors and any(error.field == column.header for error in parsed.errors):
                    continue
                if column.lookup:
                    self._resolve_lookup(db, column, value, parsed)
                elif value is not None or column.default is not None:
                    parsed.data[column.target_field] = value if value is not None else column.default
            rows.append(parsed)
        return rows

    def _coerce_value(self, column: ImportColumnSpec, raw_value: Any, errors: list[ImportRowError], row_number: int) -> Any:
        value = self._normalize_value(raw_value)
        if value is None:
            if column.required:
                errors.append(ImportRowError(row_number=row_number, field=column.header, value=raw_value, message=f"{column.header} is required."))
            return column.default

        if column.data_type in {"string", "lookup"}:
            value = str(value).strip()
            if column.max_length is not None and len(value) > column.max_length:
                errors.append(
                    ImportRowError(
                        row_number=row_number,
                        field=column.header,
                        value=value,
                        message=f"{column.header} must be {column.max_length} characters or fewer.",
                    )
                )
            return value

        if column.data_type == "integer":
            try:
                if isinstance(value, bool):
                    raise ValueError
                if isinstance(value, float) and not value.is_integer():
                    raise ValueError
                integer_value = int(value)
            except (TypeError, ValueError):
                errors.append(ImportRowError(row_number=row_number, field=column.header, value=raw_value, message=f"{column.header} must be a whole number."))
                return None
            if column.min_value is not None and integer_value < column.min_value:
                errors.append(
                    ImportRowError(
                        row_number=row_number,
                        field=column.header,
                        value=integer_value,
                        message=f"{column.header} must be greater than or equal to {column.min_value}.",
                    )
                )
            return integer_value

        if column.data_type == "boolean":
            if isinstance(value, bool):
                return value
            text = str(value).strip().lower()
            truthy = {"true", "yes", "y", "1", "active"}
            falsy = {"false", "no", "n", "0", "inactive"}
            if text in truthy:
                return True
            if text in falsy:
                return False
            errors.append(
                ImportRowError(
                    row_number=row_number,
                    field=column.header,
                    value=raw_value,
                    message=f"{column.header} must be TRUE/FALSE, Yes/No, Active/Inactive, or 1/0.",
                )
            )
            return None

        return value

    def _resolve_lookup(self, db: Session, column: ImportColumnSpec, value: Any, row: ParsedRow) -> None:
        if value is None or not column.lookup:
            return
        lookup = column.lookup
        lookup_column = getattr(lookup.model, lookup.lookup_field)
        stmt = select(lookup.model).where(lookup_column == value)
        if hasattr(lookup.model, "is_deleted"):
            stmt = stmt.where(lookup.model.is_deleted.is_(False))
        if hasattr(lookup.model, "is_active"):
            stmt = stmt.where(lookup.model.is_active.is_(True))
        entity = db.scalar(stmt.limit(1))
        if not entity:
            row.errors.append(
                ImportRowError(
                    row_number=row.row_number,
                    field=column.header,
                    value=value,
                    message=f"{lookup.label} with {lookup.lookup_field} '{value}' was not found or is inactive.",
                )
            )
            return
        row.data[lookup.target_field] = entity.id

    def _apply_duplicate_checks(self, db: Session, spec: MasterImportSpec, rows: list[ParsedRow]) -> None:
        for unique_field in spec.unique_fields:
            occurrences: dict[Any, list[ParsedRow]] = {}
            for row in rows:
                value = row.data.get(unique_field)
                if value in (None, ""):
                    continue
                occurrences.setdefault(value, []).append(row)
            for value, duplicate_rows in occurrences.items():
                if len(duplicate_rows) > 1:
                    for row in duplicate_rows:
                        row.errors.append(
                            ImportRowError(
                                row_number=row.row_number,
                                field=unique_field,
                                value=value,
                                message=f"Duplicate value '{value}' appears multiple times in this file.",
                            )
                        )
                if db.scalar(select(spec.model.id).where(getattr(spec.model, unique_field) == value).limit(1)):
                    for row in duplicate_rows:
                        row.errors.append(
                            ImportRowError(
                                row_number=row.row_number,
                                field=unique_field,
                                value=value,
                                message=f"Value '{value}' already exists in {spec.display_name}. Phase 1 import is insert-only.",
                            )
                        )

    def _build_result(self, spec: MasterImportSpec, rows: list[ParsedRow], file_errors: list[ImportRowError]) -> ValidationResult:
        row_errors = [error for row in rows for error in row.errors]
        errors = [*file_errors, *row_errors]
        invalid_row_numbers = {error.row_number for error in row_errors if error.row_number > 0}
        invalid_rows = len(invalid_row_numbers)
        total_rows = len(rows)
        valid_rows = max(total_rows - invalid_rows, 0)
        summary = ImportValidationResponse(
            resource=spec.resource,
            total_rows=total_rows,
            valid_rows=valid_rows if not file_errors else 0,
            invalid_rows=invalid_rows,
            can_commit=total_rows > 0 and not errors,
            errors=errors,
        )
        return ValidationResult(summary=summary, rows=rows)

    def _build_data_entry_sheet(self, worksheet: Any, spec: MasterImportSpec) -> None:
        mandatory_fill = PatternFill("solid", fgColor="F97316")
        optional_fill = PatternFill("solid", fgColor="D9EAF7")
        header_font = Font(bold=True, color="111827")
        for column_index, column in enumerate(spec.columns, start=1):
            cell = worksheet.cell(row=1, column=column_index, value=column.header)
            cell.font = header_font
            cell.fill = mandatory_fill if column.required else optional_fill
            cell.alignment = Alignment(horizontal="center")
            cell.comment = Comment("Required" if column.required else "Optional", "DIA Import")
            worksheet.column_dimensions[cell.column_letter].width = max(len(column.header) + 4, 18)
            if column.data_type == "boolean":
                validation = DataValidation(type="list", formula1='"TRUE,FALSE"', allow_blank=True)
                worksheet.add_data_validation(validation)
                validation.add(f"{cell.column_letter}2:{cell.column_letter}{MAX_IMPORT_ROWS + 1}")
            if column.data_type == "integer":
                for row_number in range(2, min(MAX_IMPORT_ROWS + 1, 101) + 1):
                    worksheet.cell(row=row_number, column=column_index).number_format = "0"
        worksheet.freeze_panes = "A2"

    def _build_instructions_sheet(self, worksheet: Any, spec: MasterImportSpec) -> None:
        rows = [
            ("Template", spec.display_name),
            ("Mode", "Strict insert-only. The entire file is rejected if any row has an error."),
            ("Sheet to fill", DATA_ENTRY_SHEET),
            ("Maximum rows", str(MAX_IMPORT_ROWS)),
            ("Mandatory headers", ", ".join(column.header for column in spec.columns if column.required)),
            ("System fields", "Do not add id, created_at, updated_at, created_by, updated_by, is_deleted, or deleted_at."),
            ("Boolean values", "Use TRUE/FALSE, Yes/No, Active/Inactive, or 1/0. Blank is treated as TRUE for is_active."),
        ]
        rows.extend((f"Rule {index}", instruction) for index, instruction in enumerate(spec.instructions, start=1))
        for row_index, (label, value) in enumerate(rows, start=1):
            worksheet.cell(row=row_index, column=1, value=label).font = Font(bold=True)
            worksheet.cell(row=row_index, column=2, value=value)
        worksheet.column_dimensions["A"].width = 24
        worksheet.column_dimensions["B"].width = 110

    def _build_reference_sheet(self, db: Session, worksheet: Any, spec: MasterImportSpec) -> None:
        current_column = 1
        for column in spec.columns:
            if not column.lookup:
                continue
            lookup = column.lookup
            worksheet.cell(row=1, column=current_column, value=column.header).font = Font(bold=True)
            worksheet.cell(row=1, column=current_column + 1, value=lookup.display_field).font = Font(bold=True)
            stmt = select(lookup.model).order_by(getattr(lookup.model, lookup.lookup_field))
            if hasattr(lookup.model, "is_deleted"):
                stmt = stmt.where(lookup.model.is_deleted.is_(False))
            if hasattr(lookup.model, "is_active"):
                stmt = stmt.where(lookup.model.is_active.is_(True))
            for row_index, entity in enumerate(db.scalars(stmt).all(), start=2):
                worksheet.cell(row=row_index, column=current_column, value=getattr(entity, lookup.lookup_field))
                worksheet.cell(row=row_index, column=current_column + 1, value=getattr(entity, lookup.display_field))
            worksheet.column_dimensions[worksheet.cell(row=1, column=current_column).column_letter].width = 22
            worksheet.column_dimensions[worksheet.cell(row=1, column=current_column + 1).column_letter].width = 36
            current_column += 3

    def _normalize_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    def _has_value(self, value: Any) -> bool:
        return self._normalize_value(value) is not None


master_excel_import_service = MasterExcelImportService()
