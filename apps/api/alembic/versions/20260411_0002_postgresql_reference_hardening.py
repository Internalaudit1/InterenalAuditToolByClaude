"""postgresql reference hardening

Revision ID: 20260411_0002
Revises: 20260409_0001
Create Date: 2026-04-11 12:00:00
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260411_0002"
down_revision = "20260409_0001"
branch_labels = None
depends_on = None


def _is_blank(value: str | None) -> bool:
    return value is None or not str(value).strip()


def _next_reference(bind, counters, *, entity_name: str, prefix: str, ref_year: int, pad_length: int = 4) -> str:
    row = bind.execute(
        sa.select(counters.c.id, counters.c.last_value).where(
            counters.c.entity_name == entity_name,
            counters.c.ref_year == ref_year,
        )
    ).mappings().first()
    if row:
        next_value = int(row["last_value"]) + 1
        bind.execute(
            counters.update()
            .where(counters.c.id == row["id"])
            .values(last_value=next_value, updated_at=sa.text("CURRENT_TIMESTAMP"))
        )
    else:
        next_value = 1
        bind.execute(
            counters.insert().values(
                entity_name=entity_name,
                ref_year=ref_year,
                last_value=next_value,
            )
        )
    return f"{prefix}-{ref_year}-{next_value:0{pad_length}d}"


def _backfill_business_references(bind) -> None:
    metadata = sa.MetaData()
    counters = sa.Table("business_reference_counters", metadata, autoload_with=bind)
    audit_plans = sa.Table("audit_plans", metadata, autoload_with=bind)
    audits = sa.Table("audits", metadata, autoload_with=bind)
    action_plans = sa.Table("action_plans", metadata, autoload_with=bind)
    revisions = sa.Table("action_plan_revisions", metadata, autoload_with=bind)
    attachments = sa.Table("attachments", metadata, autoload_with=bind)

    current_year = datetime.now(UTC).year

    for row in bind.execute(
        sa.select(audit_plans.c.id, audit_plans.c.audit_number, audit_plans.c.start_date)
    ).mappings():
        if _is_blank(row["audit_number"]):
            year = row["start_date"].year if row["start_date"] else current_year
            bind.execute(
                audit_plans.update()
                .where(audit_plans.c.id == row["id"])
                .values(audit_number=_next_reference(bind, counters, entity_name="audit_plan", prefix="AUD", ref_year=year))
            )

    plan_numbers = {
        row["id"]: row["audit_number"]
        for row in bind.execute(sa.select(audit_plans.c.id, audit_plans.c.audit_number)).mappings()
    }
    for row in bind.execute(
        sa.select(audits.c.id, audits.c.audit_plan_id, audits.c.audit_number, audits.c.start_date)
    ).mappings():
        if not _is_blank(row["audit_number"]):
            continue
        if row["audit_plan_id"] and not _is_blank(plan_numbers.get(row["audit_plan_id"])):
            reference = plan_numbers[row["audit_plan_id"]]
        else:
            year = row["start_date"].year if row["start_date"] else current_year
            reference = _next_reference(bind, counters, entity_name="audit", prefix="AUD", ref_year=year)
        bind.execute(
            audits.update()
            .where(audits.c.id == row["id"])
            .values(audit_number=reference)
        )

    for row in bind.execute(
        sa.select(action_plans.c.id, action_plans.c.action_plan_id, action_plans.c.observation_number)
    ).mappings():
        values: dict[str, str] = {}
        if _is_blank(row["action_plan_id"]):
            values["action_plan_id"] = _next_reference(bind, counters, entity_name="action_plan", prefix="ACT", ref_year=current_year)
        if _is_blank(row["observation_number"]):
            values["observation_number"] = _next_reference(bind, counters, entity_name="observation", prefix="OBS", ref_year=current_year)
        if values:
            bind.execute(
                action_plans.update()
                .where(action_plans.c.id == row["id"])
                .values(**values)
            )

    for row in bind.execute(
        sa.select(revisions.c.id, revisions.c.response_code, revisions.c.revised_date)
    ).mappings():
        if _is_blank(row["response_code"]):
            year = row["revised_date"].year if row["revised_date"] else current_year
            bind.execute(
                revisions.update()
                .where(revisions.c.id == row["id"])
                .values(response_code=_next_reference(bind, counters, entity_name="management_response", prefix="MRG", ref_year=year))
            )

    for row in bind.execute(
        sa.select(attachments.c.id, attachments.c.evidence_code, attachments.c.created_at)
    ).mappings():
        if _is_blank(row["evidence_code"]):
            year = row["created_at"].year if row["created_at"] else current_year
            bind.execute(
                attachments.update()
                .where(attachments.c.id == row["id"])
                .values(evidence_code=_next_reference(bind, counters, entity_name="attachment", prefix="EVD", ref_year=year))
            )


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_check_constraint(bind, table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(constraint["name"] == constraint_name for constraint in inspector.get_check_constraints(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if not _has_table(bind, "business_reference_counters"):
        op.create_table(
            "business_reference_counters",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("entity_name", sa.String(length=100), nullable=False),
            sa.Column("ref_year", sa.Integer(), nullable=False),
            sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("entity_name", "ref_year", name="uq_business_reference_counters_entity_year"),
        )

    for table_name in (
        "countries",
        "states",
        "cities",
        "companies",
        "processes",
        "locations",
        "process_location_mappings",
        "risk_types",
        "report_considerations",
        "recommendations",
        "root_causes",
        "impacts",
        "trial_balances",
        "observation_gradings",
        "audit_escalations",
        "designations",
        "control_performance_indicators",
        "task_swap_rules",
        "knowledge_library_items",
    ):
        if not _has_column(bind, table_name, "is_active"):
            op.add_column(table_name, sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    if not _has_column(bind, "action_plan_revisions", "response_code"):
        op.add_column("action_plan_revisions", sa.Column("response_code", sa.String(length=100), nullable=True))
    if not _has_column(bind, "attachments", "evidence_code"):
        op.add_column("attachments", sa.Column("evidence_code", sa.String(length=100), nullable=True))

    for table_name, index_name, columns, unique in (
        ("action_plan_revisions", "ix_action_plan_revisions_response_code", ["response_code"], True),
        ("attachments", "ix_attachments_evidence_code", ["evidence_code"], True),
        ("attachments", "ix_attachments_owner_type_owner_id", ["owner_type", "owner_id"], False),
        ("activity_logs", "ix_activity_logs_module_entity_actor_created", ["module", "entity_type", "actor_user_id", "created_at"], False),
        ("notifications", "ix_notifications_user_read_due_date", ["user_id", "is_read", "due_date"], False),
        ("audit_plans", "ix_audit_plans_company_location_quarter", ["company_id", "location_id", "quarter"], False),
        ("audit_plans", "ix_audit_plans_fiscal_year_planned_flag", ["fiscal_year", "planned_flag"], False),
        ("audits", "ix_audits_status_company_location", ["status", "company_id", "location_id"], False),
        ("audits", "ix_audits_quarter_planned_flag_end_date", ["quarter", "planned_flag", "end_date"], False),
        ("process_risk_mappings", "ix_process_risk_mappings_audit_plan_id", ["audit_plan_id"], False),
        ("erm_risks", "ix_erm_risks_audit_plan_process", ["audit_plan_id", "process_id"], False),
        ("business_initiatives", "ix_business_initiatives_audit_plan_owner", ["audit_plan_id", "owner_user_id"], False),
        ("overall_assessments", "ix_overall_assessments_audit_plan_location", ["audit_plan_id", "location_id"], False),
        ("overall_assessments", "ix_overall_assessments_coverage_status", ["coverage_status"], False),
        ("action_plans", "ix_action_plans_audit_location_status", ["audit_id", "location_id", "auditor_status", "auditee_status"], False),
        ("action_plans", "ix_action_plans_timeline_and_assignments", ["agreed_timeline", "observation_grading_id", "implementation_owner_user_id", "assigned_auditor_user_id"], False),
        ("action_plan_revisions", "ix_action_plan_revisions_action_plan_revised_date", ["action_plan_id", "revised_date"], False),
        ("locations", "ix_locations_company_profit_center", ["company_id", "profit_center_code"], False),
        ("process_location_mappings", "ix_process_location_mappings_process_location", ["process_id", "location_id"], False),
        ("refresh_tokens", "ix_refresh_tokens_user_expires", ["user_id", "expires_at"], False),
    ):
        if not _has_index(bind, table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=unique)

    if dialect != "sqlite":
        for table_name, constraint_name, condition in (
            ("audit_plans", "ck_audit_plans_date_range", "end_date >= start_date"),
            ("audits", "ck_audits_date_range", "end_date >= start_date"),
            ("audits", "ck_audits_status_valid", "status IN ('To be Initiated', 'In Progress', 'Completed', 'Overdue', 'Unplanned')"),
            ("overall_assessments", "ck_overall_assessments_coverage_status_valid", "coverage_status IN ('Covered', 'Not Covered')"),
            ("action_plans", "ck_action_plans_auditor_status_valid", "auditor_status IN ('Pending to be initiated', 'In Progress', 'Under Review', 'Completed', 'Reopened')"),
            ("action_plans", "ck_action_plans_auditee_status_valid", "auditee_status IN ('Pending to be initiated', 'In Progress', 'Under Review', 'Completed', 'Reopened')"),
            ("action_plans", "ck_action_plans_revision_count_non_negative", "revision_count >= 0"),
            ("observation_gradings", "ck_observation_gradings_severity_rank_positive", "severity_rank > 0"),
            ("attachments", "ck_attachments_file_size_non_negative", "file_size >= 0"),
            ("refresh_tokens", "ck_refresh_tokens_expiry_after_create", "expires_at > created_at"),
        ):
            if not _has_check_constraint(bind, table_name, constraint_name):
                op.create_check_constraint(constraint_name, table_name, condition)

    _backfill_business_references(bind)

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION next_business_ref(p_entity_name TEXT, p_prefix TEXT, p_ref_year INTEGER, p_pad_length INTEGER DEFAULT 4)
            RETURNS TEXT AS $$
            DECLARE
                v_next INTEGER;
            BEGIN
                INSERT INTO business_reference_counters (entity_name, ref_year, last_value, created_at, updated_at)
                VALUES (p_entity_name, p_ref_year, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (entity_name, ref_year)
                DO UPDATE SET
                    last_value = business_reference_counters.last_value + 1,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING last_value INTO v_next;

                RETURN format('%s-%s-%s', p_prefix, p_ref_year, lpad(v_next::text, p_pad_length, '0'));
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_audit_plan_number()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.audit_number IS NULL OR btrim(NEW.audit_number) = '' THEN
                    NEW.audit_number := next_business_ref('audit_plan', 'AUD', COALESCE(EXTRACT(YEAR FROM NEW.start_date)::INTEGER, EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER), 4);
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_audit_number()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.audit_number IS NULL OR btrim(NEW.audit_number) = '' THEN
                    IF NEW.audit_plan_id IS NOT NULL THEN
                        SELECT audit_number INTO NEW.audit_number
                        FROM audit_plans
                        WHERE id = NEW.audit_plan_id;
                    END IF;
                    IF NEW.audit_number IS NULL OR btrim(NEW.audit_number) = '' THEN
                        NEW.audit_number := next_business_ref('audit', 'AUD', COALESCE(EXTRACT(YEAR FROM NEW.start_date)::INTEGER, EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER), 4);
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_action_plan_references()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.audit_number IS NULL OR btrim(NEW.audit_number) = '' THEN
                    SELECT audit_number INTO NEW.audit_number
                    FROM audits
                    WHERE id = NEW.audit_id;
                END IF;
                IF NEW.action_plan_id IS NULL OR btrim(NEW.action_plan_id) = '' THEN
                    NEW.action_plan_id := next_business_ref('action_plan', 'ACT', EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 4);
                END IF;
                IF NEW.observation_number IS NULL OR btrim(NEW.observation_number) = '' THEN
                    NEW.observation_number := next_business_ref('observation', 'OBS', EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 4);
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_response_code()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.response_code IS NULL OR btrim(NEW.response_code) = '' THEN
                    NEW.response_code := next_business_ref('management_response', 'MRG', COALESCE(EXTRACT(YEAR FROM NEW.revised_date)::INTEGER, EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER), 4);
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_evidence_code()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.evidence_code IS NULL OR btrim(NEW.evidence_code) = '' THEN
                    NEW.evidence_code := next_business_ref('attachment', 'EVD', EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 4);
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_business_reference_update()
            RETURNS trigger AS $$
            DECLARE
                column_name TEXT;
            BEGIN
                FOREACH column_name IN ARRAY TG_ARGV LOOP
                    IF to_jsonb(NEW)->>column_name IS DISTINCT FROM to_jsonb(OLD)->>column_name THEN
                        RAISE EXCEPTION '% is immutable after insert', column_name;
                    END IF;
                END LOOP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute("DROP TRIGGER IF EXISTS trg_audit_plans_generate_number ON audit_plans")
        op.execute("CREATE TRIGGER trg_audit_plans_generate_number BEFORE INSERT ON audit_plans FOR EACH ROW EXECUTE FUNCTION generate_audit_plan_number()")
        op.execute("DROP TRIGGER IF EXISTS trg_audits_generate_number ON audits")
        op.execute("CREATE TRIGGER trg_audits_generate_number BEFORE INSERT ON audits FOR EACH ROW EXECUTE FUNCTION generate_audit_number()")
        op.execute("DROP TRIGGER IF EXISTS trg_action_plans_generate_refs ON action_plans")
        op.execute("CREATE TRIGGER trg_action_plans_generate_refs BEFORE INSERT ON action_plans FOR EACH ROW EXECUTE FUNCTION generate_action_plan_references()")
        op.execute("DROP TRIGGER IF EXISTS trg_action_plan_revisions_generate_code ON action_plan_revisions")
        op.execute("CREATE TRIGGER trg_action_plan_revisions_generate_code BEFORE INSERT ON action_plan_revisions FOR EACH ROW EXECUTE FUNCTION generate_response_code()")
        op.execute("DROP TRIGGER IF EXISTS trg_attachments_generate_code ON attachments")
        op.execute("CREATE TRIGGER trg_attachments_generate_code BEFORE INSERT ON attachments FOR EACH ROW EXECUTE FUNCTION generate_evidence_code()")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_plans_immutable_ref ON audit_plans")
        op.execute("CREATE TRIGGER trg_audit_plans_immutable_ref BEFORE UPDATE ON audit_plans FOR EACH ROW EXECUTE FUNCTION prevent_business_reference_update('audit_number')")
        op.execute("DROP TRIGGER IF EXISTS trg_audits_immutable_ref ON audits")
        op.execute("CREATE TRIGGER trg_audits_immutable_ref BEFORE UPDATE ON audits FOR EACH ROW EXECUTE FUNCTION prevent_business_reference_update('audit_number')")
        op.execute("DROP TRIGGER IF EXISTS trg_action_plans_immutable_ref ON action_plans")
        op.execute("CREATE TRIGGER trg_action_plans_immutable_ref BEFORE UPDATE ON action_plans FOR EACH ROW EXECUTE FUNCTION prevent_business_reference_update('action_plan_id', 'observation_number')")
        op.execute("DROP TRIGGER IF EXISTS trg_action_plan_revisions_immutable_ref ON action_plan_revisions")
        op.execute("CREATE TRIGGER trg_action_plan_revisions_immutable_ref BEFORE UPDATE ON action_plan_revisions FOR EACH ROW EXECUTE FUNCTION prevent_business_reference_update('response_code')")
        op.execute("DROP TRIGGER IF EXISTS trg_attachments_immutable_ref ON attachments")
        op.execute("CREATE TRIGGER trg_attachments_immutable_ref BEFORE UPDATE ON attachments FOR EACH ROW EXECUTE FUNCTION prevent_business_reference_update('evidence_code')")


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        for table_name, trigger_name in (
            ("audit_plans", "trg_audit_plans_generate_number"),
            ("audits", "trg_audits_generate_number"),
            ("action_plans", "trg_action_plans_generate_refs"),
            ("action_plan_revisions", "trg_action_plan_revisions_generate_code"),
            ("attachments", "trg_attachments_generate_code"),
            ("audit_plans", "trg_audit_plans_immutable_ref"),
            ("audits", "trg_audits_immutable_ref"),
            ("action_plans", "trg_action_plans_immutable_ref"),
            ("action_plan_revisions", "trg_action_plan_revisions_immutable_ref"),
            ("attachments", "trg_attachments_immutable_ref"),
        ):
            op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}")
        op.execute("DROP FUNCTION IF EXISTS prevent_business_reference_update()")
        op.execute("DROP FUNCTION IF EXISTS generate_evidence_code()")
        op.execute("DROP FUNCTION IF EXISTS generate_response_code()")
        op.execute("DROP FUNCTION IF EXISTS generate_action_plan_references()")
        op.execute("DROP FUNCTION IF EXISTS generate_audit_number()")
        op.execute("DROP FUNCTION IF EXISTS generate_audit_plan_number()")
        op.execute("DROP FUNCTION IF EXISTS next_business_ref(TEXT, TEXT, INTEGER, INTEGER)")

    for index_name, table_name in (
        ("ix_refresh_tokens_user_expires", "refresh_tokens"),
        ("ix_process_location_mappings_process_location", "process_location_mappings"),
        ("ix_locations_company_profit_center", "locations"),
        ("ix_action_plan_revisions_action_plan_revised_date", "action_plan_revisions"),
        ("ix_action_plans_timeline_and_assignments", "action_plans"),
        ("ix_action_plans_audit_location_status", "action_plans"),
        ("ix_overall_assessments_coverage_status", "overall_assessments"),
        ("ix_overall_assessments_audit_plan_location", "overall_assessments"),
        ("ix_business_initiatives_audit_plan_owner", "business_initiatives"),
        ("ix_erm_risks_audit_plan_process", "erm_risks"),
        ("ix_process_risk_mappings_audit_plan_id", "process_risk_mappings"),
        ("ix_audits_quarter_planned_flag_end_date", "audits"),
        ("ix_audits_status_company_location", "audits"),
        ("ix_audit_plans_fiscal_year_planned_flag", "audit_plans"),
        ("ix_audit_plans_company_location_quarter", "audit_plans"),
        ("ix_notifications_user_read_due_date", "notifications"),
        ("ix_activity_logs_module_entity_actor_created", "activity_logs"),
        ("ix_attachments_owner_type_owner_id", "attachments"),
        ("ix_attachments_evidence_code", "attachments"),
        ("ix_action_plan_revisions_response_code", "action_plan_revisions"),
    ):
        op.drop_index(index_name, table_name=table_name)

    if dialect != "sqlite":
        for table_name, constraint_name in (
            ("refresh_tokens", "ck_refresh_tokens_expiry_after_create"),
            ("attachments", "ck_attachments_file_size_non_negative"),
            ("observation_gradings", "ck_observation_gradings_severity_rank_positive"),
            ("action_plans", "ck_action_plans_revision_count_non_negative"),
            ("action_plans", "ck_action_plans_auditee_status_valid"),
            ("action_plans", "ck_action_plans_auditor_status_valid"),
            ("overall_assessments", "ck_overall_assessments_coverage_status_valid"),
            ("audits", "ck_audits_status_valid"),
            ("audits", "ck_audits_date_range"),
            ("audit_plans", "ck_audit_plans_date_range"),
        ):
            op.drop_constraint(constraint_name, table_name, type_="check")

    op.drop_column("attachments", "evidence_code")
    op.drop_column("action_plan_revisions", "response_code")

    for table_name in (
        "knowledge_library_items",
        "task_swap_rules",
        "control_performance_indicators",
        "designations",
        "audit_escalations",
        "observation_gradings",
        "trial_balances",
        "impacts",
        "root_causes",
        "recommendations",
        "report_considerations",
        "risk_types",
        "process_location_mappings",
        "locations",
        "processes",
        "companies",
        "cities",
        "states",
        "countries",
    ):
        op.drop_column(table_name, "is_active")

    op.drop_table("business_reference_counters")
