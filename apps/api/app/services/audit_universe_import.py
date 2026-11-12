from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction
from app.core.exceptions import ValidationException
from app.models import City, Company, Country, Location, Process, ProcessLocationMapping, State
from app.schemas.imports import (
    AuditUniverseCandidate,
    AuditUniverseCommitResponse,
    AuditUniverseValidationResponse,
    ImportRowError,
)
from app.services.activity_log import activity_log_service
from app.services.excel_import import XLSX_MEDIA_TYPE

MAX_ANNUAL_PLAN_ROWS = 1000
REQUIRED_HEADERS = {"Audit Area", "Audit Name / Unit Name"}
TEMPLATE_HEADERS = [
    "S. No.",
    "Audit Area",
    "Audit Name / Unit Name",
    "Period",
    "Executor",
    "Mentor",
    "Audit SPOC",
    "Audit Commencement Date",
    "Qtr",
    "Audit Program Date",
    "IDR Date",
    "Audit Fieldwork Target Date",
    "Tentative Target Date for Release of DR",
    "Target Date for Release of FR",
    "Current Audit Status",
    "Remarks",
]


@dataclass(frozen=True)
class UnitMapping:
    company_name: str
    location_name: str
    source_value: str


@dataclass
class AnnualPlanRow:
    row_number: int
    audit_area: str
    unit_name: str


@dataclass
class UniversePlan:
    total_rows: int = 0
    rows: list[AnnualPlanRow] = field(default_factory=list)
    companies: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    locations: dict[tuple[str, str], set[str]] = field(default_factory=lambda: defaultdict(set))
    processes: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    mappings: dict[tuple[str, str, str], set[str]] = field(default_factory=lambda: defaultdict(set))
    unresolved: list[ImportRowError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def usable_rows(self) -> int:
        unresolved_rows = {error.row_number for error in self.unresolved if error.row_number > 0}
        return max(len(self.rows) - len(unresolved_rows), 0)


class AuditUniverseImportService:
    def template_filename(self) -> str:
        return "annual-audit-universe-template.xlsx"

    def generate_template(self) -> bytes:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Annual_Audit_Plan"
        instructions = workbook.create_sheet("Instructions")
        references = workbook.create_sheet("Reference_Values")

        header_fill = PatternFill("solid", fgColor="4472C4")
        required_fill = PatternFill("solid", fgColor="F97316")
        header_font = Font(bold=True, color="FFFFFF")
        for column_index, header in enumerate(TEMPLATE_HEADERS, start=1):
            cell = worksheet.cell(row=1, column=column_index, value=header)
            cell.font = header_font
            cell.fill = required_fill if header in REQUIRED_HEADERS else header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            worksheet.column_dimensions[cell.column_letter].width = max(18, min(len(header) + 4, 34))
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = f"A1:{worksheet.cell(row=1, column=len(TEMPLATE_HEADERS)).column_letter}1"

        quarter_validation = DataValidation(type="list", formula1='"Q1,Q2,Q3,Q4"', allow_blank=True)
        worksheet.add_data_validation(quarter_validation)
        quarter_validation.add("I2:I1001")

        status_validation = DataValidation(type="list", formula1='"WIP,Attention Required,FR Released,DR Released,Not Applicable"', allow_blank=True)
        worksheet.add_data_validation(status_validation)
        status_validation.add("O2:O1001")

        sample_rows = [
            [1, "ITGC", "HCL Corporation Pvt. Ltd.", "FY 26-27", "Ravi", "", "Rohan", None, "Q1", None, None, None, None, None, "WIP", ""],
            [2, "Treasury", "Treasury", "FY 26-27", "Sajal / Ravi", "", "Rohan", None, "Q2", None, None, None, None, None, "", ""],
        ]
        for row in sample_rows:
            worksheet.append(row)

        instruction_rows = [
            ("Purpose", "Use this template to build reusable Company, Location, Process, and Process Location Mapping master data."),
            ("Required columns", "Audit Area and Audit Name / Unit Name are mandatory for universe setup."),
            ("Audit Area", "Enter the recurring audit area/process, for example ITGC, Treasury, Administration, HR & Payroll."),
            ("Audit Name / Unit Name", "Enter the company, site, auditable unit, or virtual group such as All Entities or NBFC Entities."),
            ("Executor", "Optional. In your current convention this represents junior auditor input and is not used to create master universe records."),
            ("Audit SPOC", "Optional. In your current convention this represents lead auditor input and is not used to create master universe records."),
            ("Commit behavior", "The upload creates or reuses reusable master data only. It does not create annual Audit Plans."),
            ("Review behavior", "Person-like or ambiguous unit values are kept in the issue report instead of being created as companies or locations."),
        ]
        for row_index, (label, value) in enumerate(instruction_rows, start=1):
            instructions.cell(row=row_index, column=1, value=label).font = Font(bold=True)
            instructions.cell(row=row_index, column=2, value=value)
        instructions.column_dimensions["A"].width = 26
        instructions.column_dimensions["B"].width = 120

        reference_rows = [
            ("Column", "Accepted / Example Values"),
            ("Qtr", "Q1, Q2, Q3, Q4"),
            ("Current Audit Status", "WIP, Attention Required, FR Released, DR Released, Not Applicable"),
            ("Company alias examples", "KNMA -> Kiran Nadar Museum of Art; SNIOE -> Shiv Nadar Institution of Eminence"),
            ("Virtual location examples", "All Entities, NBFC Entities, Treasury, Shared Application"),
        ]
        for row_index, (label, value) in enumerate(reference_rows, start=1):
            references.cell(row=row_index, column=1, value=label).font = Font(bold=True)
            references.cell(row=row_index, column=2, value=value)
        references.column_dimensions["A"].width = 30
        references.column_dimensions["B"].width = 100

        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def validate_workbook(self, db: Session, file_bytes: bytes, filename: str | None) -> AuditUniverseValidationResponse:
        plan = self._build_plan(db, file_bytes, filename)
        return self._to_response(db, plan)

    def commit_workbook(
        self,
        db: Session,
        file_bytes: bytes,
        filename: str | None,
        actor_name: str,
        actor_id: int | None,
    ) -> AuditUniverseCommitResponse:
        plan = self._build_plan(db, file_bytes, filename)
        validation = self._to_response(db, plan)
        if not validation.can_commit:
            return AuditUniverseCommitResponse(
                created=self._empty_counts(),
                reused=self._empty_counts(),
                skipped_rows=validation.unresolved_rows,
                message="Audit universe was not created because the workbook has no usable rows.",
                validation=validation,
            )

        country, state, city = self._default_geography(db)
        created = self._empty_counts()
        reused = self._empty_counts()
        company_by_name: dict[str, Company] = {}
        location_by_key: dict[tuple[str, str], Location] = {}
        process_by_name: dict[str, Process] = {}

        for company_name in sorted(plan.companies):
            company = self._find_company(db, company_name)
            if company:
                reused["companies"] += 1
            else:
                company = Company(
                    name=company_name,
                    country_id=country.id,
                    state_id=state.id,
                    city_id=city.id,
                    pan=self._placeholder_tax_id("PAN", company_name),
                    gst_no=self._placeholder_tax_id("GST", company_name),
                    approver_config=None,
                    is_active=True,
                    created_by=actor_name,
                    updated_by=actor_name,
                )
                db.add(company)
                db.flush()
                created["companies"] += 1
            company_by_name[company_name] = company

        reserved_location_codes: set[str] = set()
        for company_name, location_name in sorted(plan.locations):
            company = company_by_name[company_name]
            location = self._find_location(db, company.id, location_name)
            if location:
                reused["locations"] += 1
            else:
                location = Location(
                    sector="Annual Audit Universe",
                    country_id=company.country_id,
                    state_id=company.state_id,
                    city_id=company.city_id,
                    company_id=company.id,
                    location_code=self._unique_code(db, Location, "location_code", self._location_code(company_name, location_name), reserved_location_codes),
                    risk_index="Medium",
                    description=location_name,
                    is_active=True,
                    created_by=actor_name,
                    updated_by=actor_name,
                )
                db.add(location)
                db.flush()
                created["locations"] += 1
            location_by_key[(company_name, location_name)] = location

        reserved_process_codes: set[str] = set()
        for process_name in sorted(plan.processes):
            process = self._find_process(db, process_name)
            if process:
                reused["processes"] += 1
            else:
                process = Process(
                    code=self._unique_code(db, Process, "code", self._code_from_text(process_name), reserved_process_codes),
                    sector="Internal Audit",
                    business_cycle="Annual Audit Universe",
                    name=process_name,
                    description="Auto-created from the approved annual audit plan workbook.",
                    is_active=True,
                    created_by=actor_name,
                    updated_by=actor_name,
                )
                db.add(process)
                db.flush()
                created["processes"] += 1
            process_by_name[process_name] = process

        reserved_mapping_codes: set[str] = set()
        for company_name, location_name, process_name in sorted(plan.mappings):
            company = company_by_name[company_name]
            location = location_by_key[(company_name, location_name)]
            process = process_by_name[process_name]
            mapping = self._find_mapping(db, company.id, location.id, process.id)
            if mapping:
                reused["mappings"] += 1
                continue
            mapping = ProcessLocationMapping(
                code=self._unique_code(
                    db,
                    ProcessLocationMapping,
                    "code",
                    self._mapping_code(company_name, location_name, process_name),
                    reserved_mapping_codes,
                ),
                audit_name=f"{process_name} - {location_name}",
                process_id=process.id,
                location_id=location.id,
                company_id=company.id,
                is_active=True,
                created_by=actor_name,
                updated_by=actor_name,
            )
            db.add(mapping)
            db.flush()
            created["mappings"] += 1

        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="audit_universe_import",
            entity_type="AuditUniverse",
            entity_id="bulk",
            action_type=ActivityAction.IMPORT.value,
            new_values={"created": created, "reused": reused, "skipped_rows": validation.unresolved_rows},
        )

        refreshed_validation = self._to_response(db, plan)
        return AuditUniverseCommitResponse(
            created=created,
            reused=reused,
            skipped_rows=validation.unresolved_rows,
            message=(
                "Audit universe master data prepared: "
                f"{created['companies']} companies, {created['locations']} locations, "
                f"{created['processes']} processes, and {created['mappings']} process-location mappings created."
            ),
            validation=refreshed_validation,
        )

    def generate_error_report(self, db: Session, file_bytes: bytes, filename: str | None) -> bytes:
        validation = self.validate_workbook(db, file_bytes, filename)
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Audit_Universe_Issues"
        headers = ["row_number", "field", "value", "message"]
        for column_index, header in enumerate(headers, start=1):
            cell = worksheet.cell(row=1, column=column_index, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="B91C1C")
        for row_index, error in enumerate(validation.unresolved, start=2):
            worksheet.cell(row=row_index, column=1, value=error.row_number or "File")
            worksheet.cell(row=row_index, column=2, value=error.field or "Workbook")
            worksheet.cell(row=row_index, column=3, value=None if error.value is None else str(error.value))
            worksheet.cell(row=row_index, column=4, value=error.message)
        if not validation.unresolved:
            worksheet.cell(row=2, column=4, value="No unresolved rows were found.")
        for column in worksheet.columns:
            width = min(max(len(str(cell.value or "")) for cell in column) + 2, 80)
            worksheet.column_dimensions[column[0].column_letter].width = width
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def error_report_filename(self) -> str:
        return "audit-universe-import-issues.xlsx"

    def _build_plan(self, db: Session, file_bytes: bytes, filename: str | None) -> UniversePlan:
        if not filename or not filename.lower().endswith(".xlsx"):
            return UniversePlan(
                unresolved=[
                    ImportRowError(row_number=0, field=None, value=filename, message="Only .xlsx annual audit-plan workbooks are supported.")
                ]
            )
        try:
            workbook = load_workbook(BytesIO(file_bytes), data_only=True)
        except Exception as exc:
            return UniversePlan(unresolved=[ImportRowError(row_number=0, field=None, value=None, message=f"Unable to read workbook: {exc}")])

        worksheet = workbook.active
        header_row, columns = self._find_headers(worksheet)
        if not header_row:
            return UniversePlan(
                unresolved=[
                    ImportRowError(
                        row_number=0,
                        field=None,
                        value=", ".join(sorted(REQUIRED_HEADERS)),
                        message="Could not find the approved audit-plan headers in the workbook.",
                    )
                ]
            )

        plan = UniversePlan()
        people_values = self._collect_people_values(worksheet, header_row, columns)
        for row_number in range(header_row + 1, worksheet.max_row + 1):
            audit_area = self._clean_text(worksheet.cell(row=row_number, column=columns["Audit Area"]).value)
            unit_name = self._clean_text(worksheet.cell(row=row_number, column=columns["Audit Name / Unit Name"]).value)
            if not audit_area and not unit_name:
                continue
            if not audit_area or not unit_name:
                continue
            if len(plan.rows) >= MAX_ANNUAL_PLAN_ROWS:
                plan.unresolved.append(
                    ImportRowError(
                        row_number=0,
                        field=None,
                        value=MAX_ANNUAL_PLAN_ROWS,
                        message=f"Workbook exceeds the maximum of {MAX_ANNUAL_PLAN_ROWS} annual-plan rows.",
                    )
                )
                break
            process_name = self._canonical_process_name(audit_area)
            row = AnnualPlanRow(row_number=row_number, audit_area=process_name, unit_name=unit_name)
            plan.rows.append(row)
            plan.processes[process_name].add(audit_area)
            mapping = self._map_unit(unit_name, people_values)
            if not mapping:
                plan.unresolved.append(
                    ImportRowError(
                        row_number=row_number,
                        field="Audit Name / Unit Name",
                        value=unit_name,
                        message="Could not safely map this value to Company + Location. It may be a person, activity, or unsupported alias.",
                    )
                )
                continue
            plan.companies[mapping.company_name].add(mapping.source_value)
            plan.locations[(mapping.company_name, mapping.location_name)].add(mapping.source_value)
            plan.mappings[(mapping.company_name, mapping.location_name, process_name)].add(f"Excel row {row_number}")

        plan.total_rows = len(plan.rows)
        if plan.total_rows == 0 and not plan.unresolved:
            plan.unresolved.append(ImportRowError(row_number=0, field=None, value=None, message="Workbook contains no audit-plan data rows."))
        self._append_geography_warning(db, plan)
        return plan

    def _to_response(self, db: Session, plan: UniversePlan) -> AuditUniverseValidationResponse:
        candidates: list[AuditUniverseCandidate] = []
        counts = Counter()

        for company_name, source_values in sorted(plan.companies.items()):
            action = "existing" if self._find_company(db, company_name) else "create"
            counts[f"companies_{action}"] += 1
            candidates.append(
                AuditUniverseCandidate(
                    kind="company",
                    action=action,
                    name=company_name,
                    row_count=len(source_values),
                    source_values=sorted(source_values),
                )
            )

        for (company_name, location_name), source_values in sorted(plan.locations.items()):
            company = self._find_company(db, company_name)
            existing = self._find_location(db, company.id, location_name) if company else None
            action = "existing" if existing else "create"
            counts[f"locations_{action}"] += 1
            candidates.append(
                AuditUniverseCandidate(
                    kind="location",
                    action=action,
                    name=location_name,
                    code=self._location_code(company_name, location_name),
                    company_name=company_name,
                    row_count=len(source_values),
                    source_values=sorted(source_values),
                )
            )

        for process_name, source_values in sorted(plan.processes.items()):
            action = "existing" if self._find_process(db, process_name) else "create"
            counts[f"processes_{action}"] += 1
            candidates.append(
                AuditUniverseCandidate(
                    kind="process",
                    action=action,
                    name=process_name,
                    code=self._code_from_text(process_name),
                    row_count=len(source_values),
                    source_values=sorted(source_values),
                )
            )

        for (company_name, location_name, process_name), source_values in sorted(plan.mappings.items()):
            company = self._find_company(db, company_name)
            location = self._find_location(db, company.id, location_name) if company else None
            process = self._find_process(db, process_name)
            existing = self._find_mapping(db, company.id, location.id, process.id) if company and location and process else None
            action = "existing" if existing else "create"
            counts[f"mappings_{action}"] += 1
            candidates.append(
                AuditUniverseCandidate(
                    kind="process_location_mapping",
                    action=action,
                    name=f"{process_name} - {location_name}",
                    code=self._mapping_code(company_name, location_name, process_name),
                    company_name=company_name,
                    location_name=location_name,
                    process_name=process_name,
                    row_count=len(source_values),
                    source_values=sorted(source_values),
                )
            )

        summary = {
            "companies_create": counts["companies_create"],
            "companies_existing": counts["companies_existing"],
            "locations_create": counts["locations_create"],
            "locations_existing": counts["locations_existing"],
            "processes_create": counts["processes_create"],
            "processes_existing": counts["processes_existing"],
            "mappings_create": counts["mappings_create"],
            "mappings_existing": counts["mappings_existing"],
        }
        return AuditUniverseValidationResponse(
            total_rows=plan.total_rows,
            usable_rows=plan.usable_rows,
            unresolved_rows=len({error.row_number for error in plan.unresolved if error.row_number > 0}),
            can_commit=plan.usable_rows > 0 and not any(error.row_number == 0 for error in plan.unresolved),
            summary=summary,
            candidates=candidates,
            unresolved=plan.unresolved,
            warnings=plan.warnings,
        )

    def _find_headers(self, worksheet: Any) -> tuple[int | None, dict[str, int]]:
        for row_number in range(1, min(20, worksheet.max_row) + 1):
            columns: dict[str, int] = {}
            for column_number in range(1, worksheet.max_column + 1):
                value = self._clean_text(worksheet.cell(row=row_number, column=column_number).value)
                if value in REQUIRED_HEADERS or value in {"Executor", "Audit SPOC"}:
                    columns[value] = column_number
            if REQUIRED_HEADERS.issubset(columns):
                return row_number, columns
        return None, {}

    def _collect_people_values(self, worksheet: Any, header_row: int, columns: dict[str, int]) -> set[str]:
        people: set[str] = set()
        for header in ("Executor", "Audit SPOC"):
            column = columns.get(header)
            if not column:
                continue
            for row_number in range(header_row + 1, worksheet.max_row + 1):
                raw = self._clean_text(worksheet.cell(row=row_number, column=column).value)
                for part in self._split_people(raw):
                    people.add(self._normal_key(part))
        people.update(self._normal_key(name) for name in {"Abhigyan", "Anish", "Ravi", "Rohan", "Gagandeep", "Nikhil", "Executor", "Undertaken by Each Auditor"})
        return people

    def _map_unit(self, raw_value: str, people_values: set[str]) -> UnitMapping | None:
        key = self._normal_key(raw_value)
        raw_lower = raw_value.lower()
        if key in people_values:
            return None

        direct_company_aliases = {
            "hcl corporation": "HCL Corporation Pvt. Ltd.",
            "hcl corporation pvt ltd": "HCL Corporation Pvt. Ltd.",
            "hcl capital": "HCL Capital Pvt. Ltd.",
            "hcl capital pvt ltd": "HCL Capital Pvt. Ltd.",
            "vama delhi": "Vama Sundari (Delhi)",
            "vamasundari investments delhi": "Vama Sundari (Delhi)",
            "vamasundari investments delhi pvt ltd": "Vama Sundari (Delhi)",
            "hcl avitas": "HCL Avitas Private Limited",
            "hcl avitas pvt ltd": "HCL Avitas Private Limited",
            "avitas": "HCL Avitas Private Limited",
            "guvi": "GUVI Geek Network Pvt. Ltd.",
            "guvi geek network": "GUVI Geek Network Pvt. Ltd.",
            "guvi geek network pvt ltd": "GUVI Geek Network Pvt. Ltd.",
            "knma": "Kiran Nadar Museum of Art",
            "kiran nadar museum of art": "Kiran Nadar Museum of Art",
            "snioe": "Shiv Nadar Institution of Eminence",
            "hcl it city lucknow": "HCL IT City (Lucknow) Pvt. Ltd.",
            "hcl it city lucknow pvt ltd": "HCL IT City (Lucknow) Pvt. Ltd.",
            "vamasundari scholarship trust": "Vamasundari Scholarship Trust",
            "jaivik farms": "Jaivik Farms",
            "india chip": "India Chip",
            "the magic years": "The Magic Years",
            "shiksha": "Shiksha",
        }
        if key in direct_company_aliases:
            return UnitMapping(direct_company_aliases[key], "Corporate / All Locations", raw_value)

        if key in {"treasury", "all entities", "shared application", "hcl shared services pgc"}:
            return UnitMapping("HCL Group", self._title_preserving(raw_value), raw_value)
        if key == "nbfc entities":
            return UnitMapping("HCL Capital Pvt. Ltd.", "NBFC Entities", raw_value)
        if key in {"knma and snf", "snf shared services"}:
            return UnitMapping("Shiv Nadar Foundation", self._title_preserving(raw_value), raw_value)
        if key in {"snf and hcl corp"}:
            return UnitMapping("HCL Group", "SNF & HCL Corp.", raw_value)
        if key.startswith("hdfc"):
            return UnitMapping("HDFC Schools", self._title_preserving(raw_value), raw_value)
        if key.startswith("sns"):
            return UnitMapping("Shiv Nadar School", self._title_preserving(raw_value), raw_value)
        if key.startswith("vg"):
            return UnitMapping("VidyaGyan", self._title_preserving(raw_value), raw_value)
        if key.startswith("snu chennai"):
            return UnitMapping("Shiv Nadar Univ. (Chennai)", "Corporate / All Locations", raw_value)
        if key.startswith("ssni chennai"):
            return UnitMapping("SSN Trust", "SSNI Chennai", raw_value)
        if key.startswith("ssnt") or key.startswith("snt"):
            return UnitMapping("SSN Trust", self._title_preserving(raw_value), raw_value)

        company_markers = (" pvt", " private", " ltd", " limited", " trust", " foundation", " university", " museum", " institution")
        if any(marker in f" {raw_lower} " for marker in company_markers):
            return UnitMapping(self._title_preserving(raw_value), "Corporate / All Locations", raw_value)
        return None

    def _default_geography(self, db: Session) -> tuple[Country, State, City]:
        country = db.scalar(select(Country).where(func.lower(Country.name) == "india", Country.is_deleted.is_(False)).limit(1))
        if not country:
            country = db.scalar(select(Country).where(Country.is_deleted.is_(False)).order_by(Country.id).limit(1))
        if not country:
            raise ValidationException("At least one active country is required before creating audit universe companies.")

        state = db.scalar(
            select(State)
            .where(State.country_id == country.id, State.is_deleted.is_(False), func.lower(State.name).in_(["delhi", "new delhi"]))
            .limit(1)
        )
        if not state:
            state = db.scalar(select(State).where(State.country_id == country.id, State.is_deleted.is_(False)).order_by(State.id).limit(1))
        if not state:
            raise ValidationException("At least one active state is required before creating audit universe companies.")

        city = db.scalar(
            select(City)
            .where(City.state_id == state.id, City.is_deleted.is_(False), func.lower(City.name).in_(["new delhi", "delhi"]))
            .limit(1)
        )
        if not city:
            city = db.scalar(select(City).where(City.state_id == state.id, City.is_deleted.is_(False)).order_by(City.id).limit(1))
        if not city:
            raise ValidationException("At least one active city is required before creating audit universe companies.")
        return country, state, city

    def _append_geography_warning(self, db: Session, plan: UniversePlan) -> None:
        if not plan.companies:
            return
        try:
            country, state, city = self._default_geography(db)
        except ValidationException as exc:
            plan.unresolved.append(ImportRowError(row_number=0, field="geography", value=None, message=str(exc.detail)))
            return
        plan.warnings.append(
            f"New companies/locations will use default geography {country.name} / {state.name} / {city.name}; update exact geography later where required."
        )

    def _find_company(self, db: Session, name: str) -> Company | None:
        return db.scalar(select(Company).where(func.lower(Company.name) == name.lower(), Company.is_deleted.is_(False)).limit(1))

    def _find_location(self, db: Session, company_id: int, description: str) -> Location | None:
        return db.scalar(
            select(Location)
            .where(
                Location.company_id == company_id,
                func.lower(Location.description) == description.lower(),
                Location.is_deleted.is_(False),
            )
            .limit(1)
        )

    def _find_process(self, db: Session, name: str) -> Process | None:
        return db.scalar(select(Process).where(func.lower(Process.name) == name.lower(), Process.is_deleted.is_(False)).limit(1))

    def _find_mapping(self, db: Session, company_id: int, location_id: int, process_id: int) -> ProcessLocationMapping | None:
        return db.scalar(
            select(ProcessLocationMapping)
            .where(
                ProcessLocationMapping.company_id == company_id,
                ProcessLocationMapping.location_id == location_id,
                ProcessLocationMapping.process_id == process_id,
                ProcessLocationMapping.is_deleted.is_(False),
            )
            .limit(1)
        )

    def _unique_code(self, db: Session, model: type, field_name: str, base_code: str, reserved: set[str]) -> str:
        field = getattr(model, field_name)
        base = base_code[:90].rstrip("_") or "AUTO"
        candidate = base
        suffix = 2
        while candidate in reserved or db.scalar(select(model.id).where(field == candidate, model.is_deleted.is_(False)).limit(1)):
            candidate = f"{base[:85]}_{suffix}"
            suffix += 1
        reserved.add(candidate)
        return candidate

    def _placeholder_tax_id(self, prefix: str, value: str) -> str:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12].upper()
        return f"AUTO-{prefix}-{digest}"

    def _location_code(self, company_name: str, location_name: str) -> str:
        return self._code_from_text(f"LOC {company_name} {location_name}")[:100]

    def _mapping_code(self, company_name: str, location_name: str, process_name: str) -> str:
        return self._code_from_text(f"AUM {company_name} {location_name} {process_name}")[:100]

    def _code_from_text(self, value: str) -> str:
        tokens = re.findall(r"[A-Za-z0-9]+", value.upper())
        if not tokens:
            return "AUTO"
        stop_words = {"AND", "OF", "THE", "INCL", "INCLUDE", "INCLUDING", "FOR", "TO", "BY"}
        useful = [token for token in tokens if token not in stop_words]
        code = "_".join(useful[:8]) if useful else "_".join(tokens[:8])
        return code[:100]

    def _canonical_process_name(self, value: str) -> str:
        text = self._clean_text(value)
        replacements = {
            "Financial Audits - Revenue,Expenses, Assets and Liab.": "Financial Audits - Revenue, Expenses, Assets and Liabilities",
            "FCRA compliance Review": "FCRA Compliance Review",
            "KNMA Artworks  (Physical Verification)": "KNMA Artworks Physical Verification",
            "Implmentation": "Implementation",
            "Treasory": "Treasury",
            "Commerical": "Commercial",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        text = re.sub(r"\s+", " ", text).strip()
        text = text.replace(" ,", ",")
        return text

    def _title_preserving(self, value: str) -> str:
        cleaned = self._clean_text(value)
        known = {
            "hdfc": "HDFC",
            "snioe": "SNIOE",
            "knma": "KNMA",
            "guvi": "GUVI",
            "ssnt": "SSNT",
            "snu-c": "SNU-C",
            "sns": "SNS",
            "vg": "VG",
            "snf": "SNF",
            "hcl": "HCL",
        }
        words = []
        for part in re.split(r"(\W+)", cleaned):
            key = part.lower()
            words.append(known.get(key, part))
        return "".join(words)

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ""
        return re.sub(r"\s+", " ", str(value).strip())

    def _normal_key(self, value: str) -> str:
        text = value.lower().replace("&", " and ")
        text = re.sub(r"\b(pvt|private|ltd|limited)\b", "", text)
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _split_people(self, value: str) -> list[str]:
        if not value or value in {"-", "--"}:
            return []
        value = re.sub(r"\([^)]*\)", "", value)
        return [part.strip() for part in re.split(r"\s*(?:/|\+|,|&| and )\s*", value, flags=re.I) if part.strip()]

    def _empty_counts(self) -> dict[str, int]:
        return {"companies": 0, "locations": 0, "processes": 0, "mappings": 0}


audit_universe_import_service = AuditUniverseImportService()
