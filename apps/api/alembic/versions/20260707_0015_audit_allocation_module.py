"""audit allocation module and fixed audit plan columns

Revision ID: 20260707_0015
Revises: 20260605_0014
Create Date: 2026-07-07 10:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260707_0015"
down_revision = "20260605_0014"
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # 1) New fixed classification columns on audit_plans
    op.add_column("audit_plans", sa.Column("serial_no", sa.Integer(), nullable=True))
    op.add_column("audit_plans", sa.Column("audit_area", sa.String(length=255), nullable=True))
    op.add_column("audit_plans", sa.Column("caro_status", sa.String(length=20), nullable=True))
    op.add_column("audit_plans", sa.Column("audit_scope_type", sa.String(length=20), nullable=True))

    # 2) Relax assignment/date columns (these move to allocation)
    with op.batch_alter_table("audit_plans") as batch:
        batch.alter_column("quarter", existing_type=sa.String(length=10), nullable=True)
        batch.alter_column("start_date", existing_type=sa.Date(), nullable=True)
        batch.alter_column("end_date", existing_type=sa.Date(), nullable=True)
        batch.alter_column("criticality", existing_type=sa.String(length=50), nullable=True)

    # 3) New audit_allocations table
    op.create_table(
        "audit_allocations",
        sa.Column("audit_plan_id", sa.Integer(), nullable=False),
        sa.Column("allocation_code", sa.String(length=100), nullable=False),
        sa.Column("lead_auditor_user_id", sa.Integer(), nullable=False),
        sa.Column("junior_auditor_1_id", sa.Integer(), nullable=True),
        sa.Column("junior_auditor_2_id", sa.Integer(), nullable=True),
        sa.Column("mentor_user_id", sa.Integer(), nullable=True),
        sa.Column("auditee_spoc_user_id", sa.Integer(), nullable=True),
        sa.Column("auditee_spoc_auditee_id", sa.Integer(), nullable=True),
        sa.Column("period_type", sa.String(length=50), nullable=True),
        sa.Column("period_value", sa.String(length=50), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="Draft"),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("audit_id", sa.Integer(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("end_date >= start_date", name="ck_audit_allocations_date_range"),
        sa.CheckConstraint("status IN ('Draft', 'Allocated', 'Initiated', 'Cancelled')", name="ck_audit_allocations_status_valid"),
        sa.ForeignKeyConstraint(["audit_plan_id"], ["audit_plans.id"]),
        sa.ForeignKeyConstraint(["lead_auditor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["junior_auditor_1_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["junior_auditor_2_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["mentor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["auditee_spoc_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["auditee_spoc_auditee_id"], ["auditees.id"]),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("allocation_code"),
        sa.UniqueConstraint("audit_plan_id", name="uq_audit_allocations_audit_plan"),
    )
    op.create_index("ix_audit_allocations_allocation_code", "audit_allocations", ["allocation_code"], unique=True)
    op.create_index("ix_audit_allocations_status", "audit_allocations", ["status"], unique=False)

    # 4) Backfill existing plan+audit pairs into allocations so history is preserved.
    # Guarded to PostgreSQL (production target); SQLite dev DBs are populated via seed.py.
    if dialect == "postgresql":
        op.execute(
            """
        INSERT INTO audit_allocations (
            audit_plan_id, allocation_code, lead_auditor_user_id,
            junior_auditor_1_id, junior_auditor_2_id, mentor_user_id,
            period_type, period_value, start_date, end_date, status,
            audit_id, created_at, updated_at, is_deleted, created_by, updated_by
        )
        SELECT ap.id,
               'ALC-LEGACY-' || ap.id,
               ap.audit_owner_id,
               ap.junior_auditor_1_id,
               ap.junior_auditor_2_id,
               a.reviewer_user_id,
               ap.period_type,
               ap.period_value,
               ap.start_date,
               ap.end_date,
               'Initiated',
               a.id,
               CURRENT_TIMESTAMP,
               CURRENT_TIMESTAMP,
               FALSE,
               'system-backfill',
               'system-backfill'
        FROM audit_plans ap
        JOIN audits a ON a.audit_plan_id = ap.id AND a.is_deleted = FALSE
        WHERE ap.audit_owner_id IS NOT NULL
          AND ap.is_deleted = FALSE
          AND NOT EXISTS (SELECT 1 FROM audit_allocations x WHERE x.audit_plan_id = ap.id)
            """
        )


def downgrade() -> None:
    op.drop_index("ix_audit_allocations_status", table_name="audit_allocations")
    op.drop_index("ix_audit_allocations_allocation_code", table_name="audit_allocations")
    op.drop_table("audit_allocations")

    with op.batch_alter_table("audit_plans") as batch:
        batch.alter_column("criticality", existing_type=sa.String(length=50), nullable=True)
        batch.alter_column("end_date", existing_type=sa.Date(), nullable=True)
        batch.alter_column("start_date", existing_type=sa.Date(), nullable=True)
        batch.alter_column("quarter", existing_type=sa.String(length=10), nullable=True)
    op.drop_column("audit_plans", "audit_scope_type")
    op.drop_column("audit_plans", "caro_status")
    op.drop_column("audit_plans", "audit_area")
    op.drop_column("audit_plans", "serial_no")
