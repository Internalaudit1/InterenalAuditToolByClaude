"""audit lifecycle foundations

Revision ID: 20260421_0005
Revises: 20260417_0004
Create Date: 2026-04-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260421_0005"
down_revision = "20260417_0004"
branch_labels = None
depends_on = None


NEW_PERMISSIONS_BY_ROLE: dict[str, set[str]] = {
    "super_admin": {
        "planning:approve",
        "audits:assign",
        "audit_memberships:view",
        "audit_memberships:manage",
        "audit_activities:view",
        "audit_activities:manage",
        "observations:view",
        "observations:create",
        "observations:issue",
        "observations:respond",
        "observations:review",
        "observations:convert",
    },
    "head_auditor": {
        "planning:approve",
        "audits:assign",
        "audit_memberships:view",
        "audit_memberships:manage",
        "audit_activities:view",
        "audit_activities:manage",
        "observations:view",
        "observations:create",
        "observations:issue",
        "observations:review",
        "observations:convert",
    },
    "auditor": {
        "audits:assign",
        "audit_memberships:view",
        "audit_memberships:manage",
        "audit_activities:view",
        "audit_activities:manage",
        "observations:view",
        "observations:create",
        "observations:issue",
        "observations:review",
        "observations:convert",
    },
    "junior_auditor": {
        "dashboard:view",
        "audits:view",
        "audit_memberships:view",
        "audit_activities:view",
        "audit_activities:manage",
        "observations:view",
        "observations:create",
        "reports:view",
        "library:view",
        "notifications:view",
    },
    "management": {
        "audit_memberships:view",
        "audit_activities:view",
        "observations:view",
    },
    "auditee": {
        "observations:view",
        "observations:respond",
    },
}


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_constraint(bind, table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(bind)
    checks = inspector.get_check_constraints(table_name)
    uniques = inspector.get_unique_constraints(table_name)
    return any(item["name"] == constraint_name for item in checks + uniques)


def _add_column_if_missing(bind, table_name: str, column: sa.Column) -> None:
    if not _has_column(bind, table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(bind, table_name: str, index_name: str, columns: list[str], *, unique: bool = False) -> None:
    if not _has_index(bind, table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _create_fk_if_missing(bind, table_name: str, constraint_name: str, referred_table: str, local_cols: list[str], remote_cols: list[str]) -> None:
    inspector = sa.inspect(bind)
    if any(fk["name"] == constraint_name for fk in inspector.get_foreign_keys(table_name)):
        return
    op.create_foreign_key(constraint_name, table_name, referred_table, local_cols, remote_cols)


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _sync_lifecycle_permissions(bind) -> None:
    if not _has_table(bind, "roles") or not _has_table(bind, "permissions") or not _has_table(bind, "role_permissions"):
        return
    now = sa.text("CURRENT_TIMESTAMP")
    all_permissions = sorted({permission for permissions in NEW_PERMISSIONS_BY_ROLE.values() for permission in permissions})
    for permission in all_permissions:
        op.execute(
            sa.text(
                """
                INSERT INTO permissions (code, description, created_at, updated_at, created_by, updated_by, is_deleted)
                VALUES (:code, :description, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'migration', 'migration', false)
                ON CONFLICT (code) DO NOTHING
                """
            ).bindparams(code=permission, description=permission.replace(":", " ").title())
        )
    op.execute(
        sa.text(
            """
            INSERT INTO roles (code, name, description, is_system, created_at, updated_at, created_by, updated_by, is_deleted)
            VALUES ('junior_auditor', 'Junior Auditor', 'Audit team member with assigned activity and observation access.', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'migration', 'migration', false)
            ON CONFLICT (code) DO UPDATE SET is_system = true, updated_at = CURRENT_TIMESTAMP
            """
        )
    )
    for role_code, permission_codes in NEW_PERMISSIONS_BY_ROLE.items():
        for permission_code in permission_codes:
            op.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT r.id, p.id
                    FROM roles r
                    JOIN permissions p ON p.code = :permission_code
                    WHERE r.code = :role_code
                    ON CONFLICT DO NOTHING
                    """
                ).bindparams(role_code=role_code, permission_code=permission_code)
            )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    _add_column_if_missing(
        bind,
        "audit_plans",
        sa.Column("approval_status", sa.String(length=50), nullable=False, server_default="Draft"),
    )
    _add_column_if_missing(bind, "audit_plans", sa.Column("approved_by_user_id", sa.Integer(), nullable=True))
    _add_column_if_missing(bind, "audit_plans", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    if _has_column(bind, "audit_plans", "approval_status"):
        op.execute(sa.text("UPDATE audit_plans SET approval_status = 'Approved' WHERE approval_status = 'Draft'"))
    if not _has_constraint(bind, "audit_plans", "ck_audit_plans_approval_status_valid"):
        op.create_check_constraint(
            "ck_audit_plans_approval_status_valid",
            "audit_plans",
            "approval_status IN ('Draft', 'Under Review', 'Approved', 'Deferred', 'Cancelled')",
        )
    _create_fk_if_missing(bind, "audit_plans", "fk_audit_plans_approved_by_user_id_users", "users", ["approved_by_user_id"], ["id"])

    _add_column_if_missing(bind, "audits", sa.Column("reviewer_user_id", sa.Integer(), nullable=True))
    _add_column_if_missing(bind, "audits", sa.Column("auditee_spoc_user_id", sa.Integer(), nullable=True))
    _add_column_if_missing(bind, "audits", sa.Column("assignment_history", sa.JSON(), nullable=True))
    _create_fk_if_missing(bind, "audits", "fk_audits_reviewer_user_id_users", "users", ["reviewer_user_id"], ["id"])
    _create_fk_if_missing(bind, "audits", "fk_audits_auditee_spoc_user_id_users", "users", ["auditee_spoc_user_id"], ["id"])

    if not _has_table(bind, "audit_memberships"):
        op.create_table(
            "audit_memberships",
            *_base_columns(),
            sa.Column("audit_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("role_on_audit", sa.String(length=50), nullable=False),
            sa.ForeignKeyConstraint(["audit_id"], ["audits.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.CheckConstraint(
                "role_on_audit IN ('lead_auditor', 'junior_auditor', 'reviewer', 'auditee_spoc', 'observer')",
                name="ck_audit_memberships_role_valid",
            ),
            sa.UniqueConstraint("audit_id", "user_id", "role_on_audit", name="uq_audit_memberships_audit_user_role"),
        )
    else:
        _add_column_if_missing(bind, "audit_memberships", sa.Column("audit_id", sa.Integer(), nullable=True))
        _add_column_if_missing(bind, "audit_memberships", sa.Column("user_id", sa.Integer(), nullable=True))
        _add_column_if_missing(bind, "audit_memberships", sa.Column("role_on_audit", sa.String(length=50), nullable=True))
    _create_index_if_missing(bind, "audit_memberships", "ix_audit_memberships_audit_user", ["audit_id", "user_id"])
    _create_index_if_missing(bind, "audit_memberships", "ix_audit_memberships_user_role", ["user_id", "role_on_audit"])

    if not _has_table(bind, "audit_activities"):
        op.create_table(
            "audit_activities",
            *_base_columns(),
            sa.Column("audit_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("objective", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("assigned_to_user_id", sa.Integer(), nullable=True),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="Yet to Start"),
            sa.Column("remarks", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["audit_id"], ["audits.id"]),
            sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"]),
            sa.CheckConstraint(
                "status IN ('Yet to Start', 'Work in Progress', 'Completed', 'Not Applicable')",
                name="ck_audit_activities_status_valid",
            ),
        )
    else:
        _add_column_if_missing(bind, "audit_activities", sa.Column("audit_id", sa.Integer(), nullable=True))
        _add_column_if_missing(bind, "audit_activities", sa.Column("title", sa.String(length=255), nullable=True))
        _add_column_if_missing(bind, "audit_activities", sa.Column("objective", sa.Text(), nullable=True))
        _add_column_if_missing(bind, "audit_activities", sa.Column("description", sa.Text(), nullable=True))
        _add_column_if_missing(bind, "audit_activities", sa.Column("assigned_to_user_id", sa.Integer(), nullable=True))
        _add_column_if_missing(bind, "audit_activities", sa.Column("due_date", sa.Date(), nullable=True))
        _add_column_if_missing(bind, "audit_activities", sa.Column("status", sa.String(length=50), nullable=True, server_default="Yet to Start"))
        _add_column_if_missing(bind, "audit_activities", sa.Column("remarks", sa.Text(), nullable=True))
    _create_index_if_missing(bind, "audit_activities", "ix_audit_activities_audit_id", ["audit_id"])
    _create_index_if_missing(bind, "audit_activities", "ix_audit_activities_audit_assignee_status", ["audit_id", "assigned_to_user_id", "status"])
    _create_index_if_missing(bind, "audit_activities", "ix_audit_activities_due_date", ["due_date"])

    if not _has_table(bind, "observations"):
        op.create_table(
            "observations",
            *_base_columns(),
            sa.Column("observation_number", sa.String(length=100), nullable=False),
            sa.Column("audit_id", sa.Integer(), nullable=False),
            sa.Column("activity_id", sa.Integer(), nullable=True),
            sa.Column("heading", sa.String(length=255), nullable=False),
            sa.Column("background", sa.Text(), nullable=True),
            sa.Column("observation_text", sa.Text(), nullable=False),
            sa.Column("risk_implication", sa.Text(), nullable=True),
            sa.Column("recommendation", sa.Text(), nullable=True),
            sa.Column("root_cause_id", sa.Integer(), nullable=True),
            sa.Column("observation_grading_id", sa.Integer(), nullable=False),
            sa.Column("risk_type_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="Draft"),
            sa.Column("auditee_user_id", sa.Integer(), nullable=True),
            sa.Column("auditee_remark", sa.Text(), nullable=True),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["audit_id"], ["audits.id"]),
            sa.ForeignKeyConstraint(["activity_id"], ["audit_activities.id"]),
            sa.ForeignKeyConstraint(["root_cause_id"], ["root_causes.id"]),
            sa.ForeignKeyConstraint(["observation_grading_id"], ["observation_gradings.id"]),
            sa.ForeignKeyConstraint(["risk_type_id"], ["risk_types.id"]),
            sa.ForeignKeyConstraint(["auditee_user_id"], ["users.id"]),
            sa.CheckConstraint(
                "status IN ('Draft', 'Issued', 'Responded', 'Accepted', 'Converted', 'Dropped')",
                name="ck_observations_status_valid",
            ),
            sa.UniqueConstraint("observation_number", name="uq_observations_observation_number"),
        )
    else:
        _add_column_if_missing(bind, "observations", sa.Column("observation_number", sa.String(length=100), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("audit_id", sa.Integer(), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("activity_id", sa.Integer(), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("heading", sa.String(length=255), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("background", sa.Text(), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("observation_text", sa.Text(), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("risk_implication", sa.Text(), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("recommendation", sa.Text(), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("root_cause_id", sa.Integer(), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("observation_grading_id", sa.Integer(), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("risk_type_id", sa.Integer(), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("status", sa.String(length=50), nullable=True, server_default="Draft"))
        _add_column_if_missing(bind, "observations", sa.Column("auditee_user_id", sa.Integer(), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("auditee_remark", sa.Text(), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True))
        _add_column_if_missing(bind, "observations", sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True))
    _create_index_if_missing(bind, "observations", "ix_observations_observation_number", ["observation_number"], unique=True)
    _create_index_if_missing(bind, "observations", "ix_observations_audit_status", ["audit_id", "status"])
    _create_index_if_missing(bind, "observations", "ix_observations_activity_status", ["activity_id", "status"])
    _create_index_if_missing(bind, "observations", "ix_observations_auditee_status", ["auditee_user_id", "status"])

    _add_column_if_missing(bind, "action_plans", sa.Column("observation_id", sa.Integer(), nullable=True))
    _create_fk_if_missing(bind, "action_plans", "fk_action_plans_observation_id_observations", "observations", ["observation_id"], ["id"])
    _create_index_if_missing(bind, "action_plans", "ix_action_plans_observation_id", ["observation_id"])

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_observation_number()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.observation_number IS NULL OR btrim(NEW.observation_number) = '' THEN
                    NEW.observation_number := next_business_ref('observation', 'OBS', EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 4);
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute("DROP TRIGGER IF EXISTS trg_observations_generate_number ON observations")
        op.execute("CREATE TRIGGER trg_observations_generate_number BEFORE INSERT ON observations FOR EACH ROW EXECUTE FUNCTION generate_observation_number()")
        op.execute("DROP TRIGGER IF EXISTS trg_observations_immutable_ref ON observations")
        op.execute("CREATE TRIGGER trg_observations_immutable_ref BEFORE UPDATE ON observations FOR EACH ROW EXECUTE FUNCTION prevent_business_reference_update('observation_number')")

    _sync_lifecycle_permissions(bind)


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_observations_immutable_ref ON observations")
        op.execute("DROP TRIGGER IF EXISTS trg_observations_generate_number ON observations")
        op.execute("DROP FUNCTION IF EXISTS generate_observation_number()")

    if _has_index(bind, "action_plans", "ix_action_plans_observation_id"):
        op.drop_index("ix_action_plans_observation_id", table_name="action_plans")
    if _has_column(bind, "action_plans", "observation_id"):
        op.drop_constraint("fk_action_plans_observation_id_observations", "action_plans", type_="foreignkey")
        op.drop_column("action_plans", "observation_id")

    if _has_table(bind, "observations"):
        op.drop_table("observations")
    if _has_table(bind, "audit_activities"):
        op.drop_table("audit_activities")
    if _has_table(bind, "audit_memberships"):
        op.drop_table("audit_memberships")

    for table_name, column_name, fk_name in (
        ("audits", "auditee_spoc_user_id", "fk_audits_auditee_spoc_user_id_users"),
        ("audits", "reviewer_user_id", "fk_audits_reviewer_user_id_users"),
        ("audit_plans", "approved_by_user_id", "fk_audit_plans_approved_by_user_id_users"),
    ):
        if _has_column(bind, table_name, column_name):
            op.drop_constraint(fk_name, table_name, type_="foreignkey")
            op.drop_column(table_name, column_name)

    for table_name, column_name in (
        ("audits", "assignment_history"),
        ("audit_plans", "approved_at"),
        ("audit_plans", "approval_status"),
    ):
        if _has_column(bind, table_name, column_name):
            if table_name == "audit_plans" and column_name == "approval_status" and _has_constraint(bind, table_name, "ck_audit_plans_approval_status_valid"):
                op.drop_constraint("ck_audit_plans_approval_status_valid", table_name, type_="check")
            op.drop_column(table_name, column_name)
