from __future__ import annotations

from dataclasses import dataclass

from app.models import (
    AuditEscalation,
    City,
    Company,
    ControlPerformanceIndicator,
    Country,
    Designation,
    Impact,
    Location,
    ObservationGrading,
    Process,
    ProcessLocationMapping,
    Recommendation,
    ReportConsideration,
    RiskType,
    RootCause,
    State,
    TaskSwapRule,
    TrialBalance,
)


@dataclass(frozen=True)
class ImportLookupSpec:
    model: type
    lookup_field: str
    target_field: str
    display_field: str
    label: str


@dataclass(frozen=True)
class ImportColumnSpec:
    header: str
    target_field: str
    data_type: str = "string"
    required: bool = False
    max_length: int | None = None
    default: object | None = None
    min_value: int | None = None
    lookup: ImportLookupSpec | None = None


@dataclass(frozen=True)
class MasterImportSpec:
    resource: str
    display_name: str
    table_name: str
    model: type
    columns: tuple[ImportColumnSpec, ...]
    unique_fields: tuple[str, ...] = ("code",)
    instructions: tuple[str, ...] = ()

    @property
    def expected_headers(self) -> list[str]:
        return [column.header for column in self.columns]


def text_column(header: str, *, required: bool = False, max_length: int | None = 255, target_field: str | None = None) -> ImportColumnSpec:
    return ImportColumnSpec(header=header, target_field=target_field or header, data_type="string", required=required, max_length=max_length)


def active_column() -> ImportColumnSpec:
    return ImportColumnSpec(header="is_active", target_field="is_active", data_type="boolean", required=False, default=True)


def simple_code_name_spec(resource: str, display_name: str, table_name: str, model: type) -> MasterImportSpec:
    return MasterImportSpec(
        resource=resource,
        display_name=display_name,
        table_name=table_name,
        model=model,
        columns=(
            text_column("code", required=True, max_length=100),
            text_column("name", required=True),
            text_column("description", max_length=None),
            active_column(),
        ),
        instructions=(
            "Use a unique code for each row.",
            "Do not enter database IDs. System-managed fields are excluded from this template.",
            "is_active accepts TRUE/FALSE, Yes/No, Active/Inactive, or 1/0. Blank defaults to TRUE.",
        ),
    )


PHASE_ONE_MASTER_IMPORT_SPECS: dict[str, MasterImportSpec] = {
    "countries": simple_code_name_spec("countries", "Countries", "countries", Country),
    "states": MasterImportSpec(
        resource="states",
        display_name="States",
        table_name="states",
        model=State,
        columns=(
            ImportColumnSpec(
                header="country_code",
                target_field="country_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(Country, "code", "country_id", "name", "Country"),
            ),
            text_column("code", required=True, max_length=100),
            text_column("name", required=True),
            text_column("description", max_length=None),
            active_column(),
        ),
        instructions=(
            "country_code must match an active country code from the Reference_Values sheet.",
            "State code must be unique.",
            "Do not enter country_id; the system resolves country_code to the real foreign key.",
        ),
    ),
    "cities": MasterImportSpec(
        resource="cities",
        display_name="Cities",
        table_name="cities",
        model=City,
        columns=(
            ImportColumnSpec(
                header="state_code",
                target_field="state_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(State, "code", "state_id", "name", "State"),
            ),
            text_column("code", required=True, max_length=100),
            text_column("name", required=True),
            text_column("description", max_length=None),
            active_column(),
        ),
        instructions=(
            "state_code must match an active state code from the Reference_Values sheet.",
            "City code must be unique.",
            "Do not enter state_id; the system resolves state_code to the real foreign key.",
        ),
    ),
    "companies": MasterImportSpec(
        resource="companies",
        display_name="Companies",
        table_name="companies",
        model=Company,
        unique_fields=("name",),
        columns=(
            text_column("name", required=True, max_length=255),
            ImportColumnSpec(
                header="country_code",
                target_field="country_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(Country, "code", "country_id", "name", "Country"),
            ),
            ImportColumnSpec(
                header="state_code",
                target_field="state_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(State, "code", "state_id", "name", "State"),
            ),
            ImportColumnSpec(
                header="city_code",
                target_field="city_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(City, "code", "city_id", "name", "City"),
            ),
            text_column("pan", required=True, max_length=50),
            text_column("gst_no", required=True, max_length=50),
            active_column(),
        ),
        instructions=(
            "Company name must be unique.",
            "Use country_code, state_code, and city_code from the Reference_Values sheet; do not enter raw database IDs.",
            "State must belong to the selected country, and city must belong to the selected state.",
        ),
    ),
    "processes": MasterImportSpec(
        resource="processes",
        display_name="Processes",
        table_name="processes",
        model=Process,
        columns=(
            text_column("code", required=True, max_length=100),
            text_column("sector", required=True, max_length=100),
            text_column("business_cycle", required=True),
            text_column("name", required=True),
            text_column("description", max_length=None),
            active_column(),
        ),
        instructions=(
            "Process code must be unique.",
            "Sector, business_cycle, and name are mandatory because they define the process taxonomy.",
        ),
    ),
    "locations": MasterImportSpec(
        resource="locations",
        display_name="Locations",
        table_name="locations",
        model=Location,
        unique_fields=("location_code",),
        columns=(
            text_column("sector", required=True, max_length=100),
            text_column("division_id", max_length=100),
            text_column("division_description", max_length=255),
            ImportColumnSpec(
                header="country_code",
                target_field="country_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(Country, "code", "country_id", "name", "Country"),
            ),
            ImportColumnSpec(
                header="state_code",
                target_field="state_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(State, "code", "state_id", "name", "State"),
            ),
            ImportColumnSpec(
                header="city_code",
                target_field="city_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(City, "code", "city_id", "name", "City"),
            ),
            ImportColumnSpec(
                header="company_name",
                target_field="company_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(Company, "name", "company_id", "name", "Company"),
            ),
            text_column("location_code", required=True, max_length=100),
            text_column("risk_index", max_length=50),
            text_column("description", required=True, max_length=255),
            active_column(),
        ),
        instructions=(
            "Location code must be unique.",
            "Use readable lookup columns; the system resolves them to real foreign keys.",
            "State/city hierarchy is validated before import.",
        ),
    ),
    "process-location-mappings": MasterImportSpec(
        resource="process-location-mappings",
        display_name="Process Location Mappings",
        table_name="process_location_mappings",
        model=ProcessLocationMapping,
        columns=(
            text_column("code", required=True, max_length=100),
            text_column("audit_name", required=True, max_length=255),
            ImportColumnSpec(
                header="process_code",
                target_field="process_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(Process, "code", "process_id", "name", "Process"),
            ),
            ImportColumnSpec(
                header="location_code",
                target_field="location_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(Location, "location_code", "location_id", "description", "Location"),
            ),
            ImportColumnSpec(
                header="company_name",
                target_field="company_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(Company, "name", "company_id", "name", "Company"),
            ),
            ImportColumnSpec(
                header="trial_balance_code",
                target_field="trial_balance_id",
                data_type="lookup",
                required=False,
                lookup=ImportLookupSpec(TrialBalance, "code", "trial_balance_id", "name", "Trial Balance"),
            ),
            active_column(),
        ),
        instructions=(
            "Mapping code must be unique.",
            "Location must belong to the selected company.",
            "trial_balance_code is optional, but when supplied it must match an active trial balance.",
        ),
    ),
    "risk-types": simple_code_name_spec("risk-types", "Risk Types", "risk_types", RiskType),
    "root-causes": simple_code_name_spec("root-causes", "Root Causes", "root_causes", RootCause),
    "impacts": simple_code_name_spec("impacts", "Impacts", "impacts", Impact),
    "trial-balances": MasterImportSpec(
        resource="trial-balances",
        display_name="Trial Balances",
        table_name="trial_balances",
        model=TrialBalance,
        columns=(
            text_column("code", required=True, max_length=100),
            text_column("name", required=True),
            ImportColumnSpec(
                header="company_name",
                target_field="company_id",
                data_type="lookup",
                required=False,
                lookup=ImportLookupSpec(Company, "name", "company_id", "name", "Company"),
            ),
            ImportColumnSpec(header="amount", target_field="amount", data_type="decimal", required=False),
            active_column(),
        ),
        instructions=(
            "Trial balance code must be unique.",
            "company_name is optional, but when supplied it must match an active company.",
            "Amount must be a valid numeric amount with up to two decimal places.",
        ),
    ),
    "recommendations": simple_code_name_spec("recommendations", "Recommendations", "recommendations", Recommendation),
    "report-considerations": simple_code_name_spec("report-considerations", "Report Considerations", "report_considerations", ReportConsideration),
    "observation-gradings": MasterImportSpec(
        resource="observation-gradings",
        display_name="Observation Gradings",
        table_name="observation_gradings",
        model=ObservationGrading,
        columns=(
            text_column("code", required=True, max_length=100),
            text_column("name", required=True, max_length=100),
            ImportColumnSpec(header="severity_rank", target_field="severity_rank", data_type="integer", required=True, min_value=1),
            text_column("description", max_length=None),
            active_column(),
        ),
        instructions=(
            "Severity rank must be a positive whole number. Lower ranks should represent higher severity.",
            "Observation grading code must be unique.",
        ),
    ),
    "audit-escalations": MasterImportSpec(
        resource="audit-escalations",
        display_name="Audit Escalations",
        table_name="audit_escalations",
        model=AuditEscalation,
        columns=(
            text_column("code", required=True, max_length=100),
            text_column("name", required=True),
            ImportColumnSpec(header="escalation_days", target_field="escalation_days", data_type="integer", required=True, min_value=0),
            text_column("description", max_length=None),
            active_column(),
        ),
        instructions=(
            "Escalation days must be a whole number greater than or equal to zero.",
            "Audit escalation code must be unique.",
        ),
    ),
    "designations": MasterImportSpec(
        resource="designations",
        display_name="Designations",
        table_name="designations",
        model=Designation,
        columns=(
            text_column("code", required=True, max_length=100),
            text_column("title", required=True),
            text_column("description", max_length=None),
            active_column(),
        ),
        instructions=(
            "Use title for the designation display name.",
            "Designation code must be unique.",
        ),
    ),
    "control-performance-indicators": MasterImportSpec(
        resource="control-performance-indicators",
        display_name="Control Performance Indicators",
        table_name="control_performance_indicators",
        model=ControlPerformanceIndicator,
        columns=(
            text_column("code", required=True, max_length=100),
            text_column("name", required=True),
            text_column("threshold"),
            text_column("description", max_length=None),
            active_column(),
        ),
        instructions=(
            "Control performance indicator code must be unique.",
            "Threshold is optional and can hold a readable target such as >= 90%.",
        ),
    ),
    "task-swaps": MasterImportSpec(
        resource="task-swaps",
        display_name="Task Swap Rules",
        table_name="task_swap_rules",
        model=TaskSwapRule,
        columns=(
            text_column("code", required=True, max_length=100),
            ImportColumnSpec(
                header="source_designation_code",
                target_field="source_designation_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(Designation, "code", "source_designation_id", "title", "Source Designation"),
            ),
            ImportColumnSpec(
                header="target_designation_code",
                target_field="target_designation_id",
                data_type="lookup",
                required=True,
                lookup=ImportLookupSpec(Designation, "code", "target_designation_id", "title", "Target Designation"),
            ),
            ImportColumnSpec(header="max_tasks", target_field="max_tasks", data_type="integer", required=True, min_value=0),
            text_column("notes", max_length=None),
            active_column(),
        ),
        instructions=(
            "Task swap code must be unique.",
            "Source and target designation must be different.",
            "max_tasks must be zero or a positive whole number.",
        ),
    ),
}
