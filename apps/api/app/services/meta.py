from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import app.models  # noqa: F401
from sqlalchemy import MetaData, Table, asc, desc, func, inspect, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.sqltypes import Boolean, Date, DateTime, Integer, JSON, Numeric, String, Text

from app.core.exceptions import ForbiddenException, NotFoundException
from app.db.base import Base
from app.schemas.common import ListQuery, PaginationMeta
from app.schemas.meta import (
    MetaColumnResponse,
    MetaForeignKeyResponse,
    MetaLookupResponse,
    MetaRelationshipResponse,
    MetaRowsResponse,
    MetaTableResponse,
)
from app.utils.serialization import jsonable_value


@dataclass(frozen=True)
class TableOverlay:
    display_label: str
    category: str
    permission: str | None = None
    business_endpoint: str | None = None
    frontend_mode: str = "admin_read_only"
    admin_only: bool = False
    system_table: bool = False
    preferred_label_columns: tuple[str, ...] = ()


TECHNICAL_FIELDS = {
    "id",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "deleted_at",
    "is_deleted",
}

SYSTEM_MANAGED_FIELDS = TECHNICAL_FIELDS | {
    "action_plan_id",
    "audit_number",
    "evidence_code",
    "password_hash",
    "observation_number",
    "response_code",
    "last_login_at",
    "sent_at",
    "read_at",
    "completed_at",
    "last_response_at",
    "last_review_at",
}

TABLE_OVERLAYS: dict[str, TableOverlay] = {
    "process_risk_mappings": TableOverlay("Process Risk Mapping", "planning", permission="planning:view", business_endpoint="/planning/process-risk-mappings", frontend_mode="business_page"),
    "erm_risks": TableOverlay("Key ERM Risks", "planning", permission="planning:view", business_endpoint="/planning/erm-risks", frontend_mode="business_page"),
    "business_initiatives": TableOverlay("Key Business Initiatives", "planning", permission="planning:view", business_endpoint="/planning/business-initiatives", frontend_mode="business_page"),
    "overall_assessments": TableOverlay("Overall Assessments", "planning", permission="planning:view", business_endpoint="/planning/overall-assessments", frontend_mode="business_page"),
    "audit_plans": TableOverlay("Audit Plans", "planning", permission="planning:view", business_endpoint="/planning/audit-plans", frontend_mode="business_page", preferred_label_columns=("audit_number", "audit_name")),
    "audits": TableOverlay("Audits", "execution", permission="audits:view", business_endpoint="/audits", frontend_mode="business_page", preferred_label_columns=("audit_number", "audit_name")),
    "audit_memberships": TableOverlay("Audit Memberships", "execution", permission="audit_memberships:view", frontend_mode="admin_read_only", preferred_label_columns=("role_on_audit",)),
    "audit_activities": TableOverlay("Audit Activities", "execution", permission="audit_activities:view", frontend_mode="business_page", preferred_label_columns=("title",)),
    "observations": TableOverlay("Observations", "execution", permission="observations:view", frontend_mode="business_page", preferred_label_columns=("observation_number", "heading")),
    "action_plans": TableOverlay("Action Plans", "action_plans", permission="action_plans:view", business_endpoint="/action-plans", frontend_mode="business_page", preferred_label_columns=("action_plan_id", "observation_heading")),
    "knowledge_library_items": TableOverlay("Knowledge Library", "knowledge", permission="library:view", business_endpoint="/knowledge-library", frontend_mode="business_page", preferred_label_columns=("title",)),
    "countries": TableOverlay("Countries", "master", permission="masters:view", business_endpoint="/master/countries", frontend_mode="business_page"),
    "states": TableOverlay("States", "master", permission="masters:view", business_endpoint="/master/states", frontend_mode="business_page"),
    "cities": TableOverlay("Cities", "master", permission="masters:view", business_endpoint="/master/cities", frontend_mode="business_page"),
    "companies": TableOverlay("Companies", "master", permission="masters:view", business_endpoint="/master/companies", frontend_mode="business_page"),
    "processes": TableOverlay("Processes", "master", permission="masters:view", business_endpoint="/master/processes", frontend_mode="business_page"),
    "locations": TableOverlay("Locations", "master", permission="masters:view", business_endpoint="/master/locations", frontend_mode="business_page", preferred_label_columns=("location_code", "description")),
    "process_location_mappings": TableOverlay("Process Location Mappings", "master", permission="masters:view", business_endpoint="/master/process-location-mappings", frontend_mode="business_page", preferred_label_columns=("code", "audit_name")),
    "risk_types": TableOverlay("Risk Types", "master", permission="masters:view", business_endpoint="/master/risk-types", frontend_mode="business_page"),
    "report_considerations": TableOverlay("Report Considerations", "master", permission="masters:view", business_endpoint="/master/report-considerations", frontend_mode="business_page"),
    "recommendations": TableOverlay("Recommendations", "master", permission="masters:view", business_endpoint="/master/recommendations", frontend_mode="business_page"),
    "root_causes": TableOverlay("Root Causes", "master", permission="masters:view", business_endpoint="/master/root-causes", frontend_mode="business_page"),
    "impacts": TableOverlay("Impacts", "master", permission="masters:view", business_endpoint="/master/impacts", frontend_mode="business_page"),
    "trial_balances": TableOverlay("Trial Balances", "master", permission="masters:view", business_endpoint="/master/trial-balances", frontend_mode="business_page"),
    "observation_gradings": TableOverlay("Observation Gradings", "master", permission="masters:view", business_endpoint="/master/observation-gradings", frontend_mode="business_page"),
    "audit_escalations": TableOverlay("Audit Escalations", "master", permission="masters:view", business_endpoint="/master/audit-escalations", frontend_mode="business_page"),
    "designations": TableOverlay("Designations", "master", permission="masters:view", business_endpoint="/master/designations", frontend_mode="business_page", preferred_label_columns=("title", "code")),
    "control_performance_indicators": TableOverlay("Control Performance Indicators", "master", permission="masters:view", business_endpoint="/master/control-performance-indicators", frontend_mode="business_page"),
    "task_swap_rules": TableOverlay("Task Swap Rules", "master", permission="masters:view", business_endpoint="/master/task-swaps", frontend_mode="business_page"),
    "users": TableOverlay("Users", "admin", permission="users:view", business_endpoint="/admin/users", frontend_mode="admin_read_only", preferred_label_columns=("full_name", "username")),
    "activity_logs": TableOverlay("Activity Logs", "admin", permission="activity_logs:view", business_endpoint="/admin/activity-logs", frontend_mode="admin_read_only", preferred_label_columns=("action_type", "entity_type")),
    "notifications": TableOverlay("Notifications", "admin", frontend_mode="admin_read_only", admin_only=True, preferred_label_columns=("title",)),
    "action_plan_revisions": TableOverlay("Action Plan Revisions", "action_plans", frontend_mode="admin_read_only", admin_only=True, preferred_label_columns=("response_code", "revision_number")),
    "management_reviews": TableOverlay("Management Reviews", "action_plans", permission="management_reviews:view", frontend_mode="admin_read_only", preferred_label_columns=("review_decision",)),
    "attachments": TableOverlay("Attachments", "support", frontend_mode="admin_read_only", admin_only=True, preferred_label_columns=("evidence_code", "file_name")),
    "roles": TableOverlay("Roles", "system", frontend_mode="admin_read_only", admin_only=True, system_table=True, preferred_label_columns=("name", "code")),
    "permissions": TableOverlay("Permissions", "system", frontend_mode="admin_read_only", admin_only=True, system_table=True, preferred_label_columns=("code",)),
    "user_roles": TableOverlay("User Roles", "system", frontend_mode="admin_read_only", admin_only=True, system_table=True),
    "role_permissions": TableOverlay("Role Permissions", "system", frontend_mode="admin_read_only", admin_only=True, system_table=True),
    "refresh_tokens": TableOverlay("Refresh Tokens", "system", frontend_mode="admin_read_only", admin_only=True, system_table=True),
    "business_reference_counters": TableOverlay("Business Reference Counters", "system", frontend_mode="admin_read_only", admin_only=True, system_table=True, preferred_label_columns=("entity_name",)),
    "alembic_version": TableOverlay("Alembic Version", "system", frontend_mode="admin_read_only", admin_only=True, system_table=True, preferred_label_columns=("version_num",)),
}

LABEL_COLUMN_CANDIDATES = (
    "name",
    "title",
    "full_name",
    "username",
    "code",
    "audit_number",
    "action_plan_id",
    "observation_number",
    "location_code",
    "description",
    "id",
)

FIELD_LABEL_OVERRIDES = {
    "audit_owner_id": "Lead Auditor",
    "junior_auditor_1_id": "Junior Auditor 1",
    "junior_auditor_2_id": "Junior Auditor 2",
}

RESERVED_QUERY_PARAMS = {"page", "page_size", "search", "sort_by", "sort_order"}


class MetaService:
    def __init__(self) -> None:
        self._model_tables = set(Base.metadata.tables.keys())

    def _allowed_tables(self, db: Session) -> set[str]:
        inspector = inspect(db.get_bind())
        return {name for name in inspector.get_table_names() if name in self._model_tables or name == "alembic_version"}

    def _table_overlay(self, table_name: str) -> TableOverlay:
        return TABLE_OVERLAYS.get(
            table_name,
            TableOverlay(display_label=self._humanize(table_name), category="system", frontend_mode="admin_read_only", admin_only=True, system_table=True),
        )

    def _humanize(self, value: str) -> str:
        return value.replace("_", " ").replace("-", " ").title()

    def _ensure_table_supported(self, db: Session, table_name: str) -> None:
        if table_name not in self._allowed_tables(db):
            raise NotFoundException(f"Table '{table_name}' is not part of the application schema.")

    def _ensure_access(self, db: Session, table_name: str, *, permissions: list[str], role_codes: list[str]) -> None:
        self._ensure_table_supported(db, table_name)
        overlay = self._table_overlay(table_name)
        if overlay.admin_only and "super_admin" not in role_codes:
            raise ForbiddenException("You do not have permission to inspect this table.")
        if overlay.permission and overlay.permission not in permissions and "super_admin" not in role_codes:
            raise ForbiddenException("You do not have permission to inspect this table.")

    def _reflect_table(self, db: Session, table_name: str) -> Table:
        metadata = MetaData()
        return Table(table_name, metadata, autoload_with=db.get_bind())

    def _guess_label_column(self, table: Table, overlay: TableOverlay) -> str:
        columns = {column.name for column in table.columns}
        for name in overlay.preferred_label_columns:
            if name in columns:
                return name
        for name in LABEL_COLUMN_CANDIDATES:
            if name in columns:
                return name
        return next(iter(columns))

    def _input_type(self, column: Any, *, is_foreign_key: bool) -> str:
        if is_foreign_key:
            return "select"
        if isinstance(column.type, Boolean):
            return "checkbox"
        if isinstance(column.type, DateTime):
            return "datetime"
        if isinstance(column.type, Date):
            return "date"
        if isinstance(column.type, (Integer, Numeric)):
            return "number"
        if isinstance(column.type, JSON):
            return "json"
        if isinstance(column.type, Text):
            return "textarea"
        return "text"

    def _coerce_filter_value(self, column: Any, raw_value: str) -> Any:
        if raw_value == "":
            return None
        if isinstance(column.type, Boolean):
            return raw_value.lower() in {"true", "1", "yes"}
        if isinstance(column.type, Integer):
            return int(raw_value)
        if isinstance(column.type, Numeric):
            return Decimal(raw_value)
        if isinstance(column.type, DateTime):
            return datetime.fromisoformat(raw_value)
        if isinstance(column.type, Date):
            return date.fromisoformat(raw_value)
        return raw_value

    def _serialize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {key: jsonable_value(value) for key, value in row.items()}

    def _lookup_descriptor(self, table_name: str, referenced_table: str, referenced_column: str, label_column: str) -> MetaLookupResponse:
        overlay = self._table_overlay(referenced_table)
        endpoint = overlay.business_endpoint or f"/meta/tables/{referenced_table}/rows"
        return MetaLookupResponse(
            endpoint=endpoint,
            value_field=referenced_column,
            label_field=label_column,
            display_field=f"{table_name}__label",
            frontend_mode=overlay.frontend_mode,
        )

    def list_tables(self, db: Session, *, permissions: list[str], role_codes: list[str]) -> list[MetaTableResponse]:
        items: list[MetaTableResponse] = []
        for table_name in sorted(self._allowed_tables(db)):
            try:
                self._ensure_access(db, table_name, permissions=permissions, role_codes=role_codes)
            except ForbiddenException:
                continue
            overlay = self._table_overlay(table_name)
            items.append(
                MetaTableResponse(
                    table_name=table_name,
                    display_label=overlay.display_label,
                    category=overlay.category,
                    system_table=overlay.system_table,
                    has_business_route=overlay.business_endpoint is not None,
                    frontend_mode=overlay.frontend_mode,
                    endpoint=overlay.business_endpoint,
                )
            )
        return items

    def table_columns(self, db: Session, table_name: str, *, permissions: list[str], role_codes: list[str]) -> list[MetaColumnResponse]:
        self._ensure_access(db, table_name, permissions=permissions, role_codes=role_codes)
        table = self._reflect_table(db, table_name)
        overlay = self._table_overlay(table_name)
        pk_columns = {column.name for column in table.primary_key.columns}
        fk_map: dict[str, tuple[str, str]] = {}
        for foreign_key in table.foreign_keys:
            fk_map[foreign_key.parent.name] = (foreign_key.column.table.name, foreign_key.column.name)

        columns: list[MetaColumnResponse] = []
        for ordinal_position, column in enumerate(table.columns, start=1):
            foreign_key = None
            lookup = None
            if column.name in fk_map:
                referenced_table, referenced_column = fk_map[column.name]
                foreign_key = MetaForeignKeyResponse(references_table=referenced_table, references_column=referenced_column)
                referenced_table_reflection = self._reflect_table(db, referenced_table)
                label_column = self._guess_label_column(referenced_table_reflection, self._table_overlay(referenced_table))
                lookup = self._lookup_descriptor(column.name, referenced_table, referenced_column, label_column)

            system_managed = column.name in SYSTEM_MANAGED_FIELDS or column.name in pk_columns
            hidden_by_default = column.name in TECHNICAL_FIELDS
            editable = overlay.frontend_mode == "business_page" and not system_managed
            columns.append(
                MetaColumnResponse(
                    name=column.name,
                    ordinal_position=ordinal_position,
                    data_type=str(column.type),
                    nullable=column.nullable,
                    primary_key=column.name in pk_columns,
                    foreign_key=foreign_key,
                    default=str(column.server_default.arg.text) if column.server_default is not None and getattr(column.server_default, "arg", None) is not None else None,
                    suggested_display_label=FIELD_LABEL_OVERRIDES.get(column.name, self._humanize(column.name)),
                    editable=editable,
                    system_managed=system_managed,
                    hidden_by_default=hidden_by_default,
                    input_type=self._input_type(column, is_foreign_key=foreign_key is not None),
                    lookup=lookup,
                )
            )
        return columns

    def table_relationships(self, db: Session, table_name: str, *, permissions: list[str], role_codes: list[str]) -> list[MetaRelationshipResponse]:
        self._ensure_access(db, table_name, permissions=permissions, role_codes=role_codes)
        inspector = inspect(db.get_bind())
        relationships: list[MetaRelationshipResponse] = []
        for foreign_key in inspector.get_foreign_keys(table_name):
            referred_table = foreign_key.get("referred_table")
            constrained_columns = foreign_key.get("constrained_columns") or []
            referred_columns = foreign_key.get("referred_columns") or []
            for local_column, related_column in zip(constrained_columns, referred_columns):
                relationships.append(
                    MetaRelationshipResponse(
                        direction="outgoing",
                        constraint_name=foreign_key.get("name"),
                        local_column=local_column,
                        related_table=referred_table,
                        related_column=related_column,
                    )
                )

        for other_table in self._allowed_tables(db):
            if other_table == table_name:
                continue
            for foreign_key in inspector.get_foreign_keys(other_table):
                if foreign_key.get("referred_table") != table_name:
                    continue
                constrained_columns = foreign_key.get("constrained_columns") or []
                referred_columns = foreign_key.get("referred_columns") or []
                for local_column, related_column in zip(referred_columns, constrained_columns):
                    relationships.append(
                        MetaRelationshipResponse(
                            direction="incoming",
                            constraint_name=foreign_key.get("name"),
                            local_column=local_column,
                            related_table=other_table,
                            related_column=related_column,
                        )
                    )
        return relationships

    def list_rows(
        self,
        db: Session,
        table_name: str,
        query: ListQuery,
        raw_filters: dict[str, str],
        *,
        permissions: list[str],
        role_codes: list[str],
    ) -> MetaRowsResponse:
        self._ensure_access(db, table_name, permissions=permissions, role_codes=role_codes)
        table = self._reflect_table(db, table_name)
        stmt = select(table)

        if "is_deleted" in table.c:
            stmt = stmt.where(table.c.is_deleted.is_(False))

        for key, raw_value in raw_filters.items():
            if key in RESERVED_QUERY_PARAMS or key not in table.c:
                continue
            value = self._coerce_filter_value(table.c[key], raw_value)
            if value is None:
                continue
            stmt = stmt.where(table.c[key] == value)

        text_columns = [column for column in table.columns if isinstance(column.type, (String, Text))]
        if query.search and text_columns:
            stmt = stmt.where(or_(*[column.ilike(f"%{query.search}%") for column in text_columns]))

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = db.scalar(count_stmt) or 0

        if query.sort_by and query.sort_by in table.c:
            sort_column = table.c[query.sort_by]
        elif "updated_at" in table.c:
            sort_column = table.c.updated_at
        else:
            sort_column = next(iter(table.primary_key.columns), next(iter(table.columns)))
        stmt = stmt.order_by(desc(sort_column) if query.sort_order == "desc" else asc(sort_column))
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        rows = [dict(mapping) for mapping in db.execute(stmt).mappings().all()]
        self._enrich_foreign_key_labels(db, table, rows)
        items = [self._serialize_row(row) for row in rows]
        return MetaRowsResponse(items=items, meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def _enrich_foreign_key_labels(self, db: Session, table: Table, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        for foreign_key in table.foreign_keys:
            local_column = foreign_key.parent.name
            referenced_table = foreign_key.column.table.name
            referenced_column = foreign_key.column.name
            foreign_ids = sorted({row.get(local_column) for row in rows if row.get(local_column) is not None})
            if not foreign_ids:
                continue
            reference_table = self._reflect_table(db, referenced_table)
            label_column_name = self._guess_label_column(reference_table, self._table_overlay(referenced_table))
            label_column = reference_table.c[label_column_name]
            stmt = select(reference_table.c[referenced_column], label_column)
            stmt = stmt.where(reference_table.c[referenced_column].in_(foreign_ids))
            if "is_deleted" in reference_table.c:
                stmt = stmt.where(reference_table.c.is_deleted.is_(False))
            lookup_map = {
                record[referenced_column]: jsonable_value(record[label_column_name])
                for record in db.execute(stmt).mappings().all()
            }
            for row in rows:
                row[f"{local_column}__label"] = lookup_map.get(row.get(local_column))


meta_service = MetaService()
