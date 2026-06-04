"""add optional junior auditor selectors to audit plans

Revision ID: 20260421_0007
Revises: 20260421_0006
Create Date: 2026-04-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260421_0007"
down_revision = "20260421_0006"
branch_labels = None
depends_on = None


def _has_column(bind, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in sa.inspect(bind).get_columns(table_name))


def _has_index(bind, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in sa.inspect(bind).get_indexes(table_name))


def _has_fk(bind, table_name: str, fk_name: str) -> bool:
    return any(fk["name"] == fk_name for fk in sa.inspect(bind).get_foreign_keys(table_name))


def _add_column_if_missing(bind, table_name: str, column: sa.Column) -> None:
    if not _has_column(bind, table_name, column.name):
        op.add_column(table_name, column)


def _create_fk_if_missing(bind, table_name: str, fk_name: str, referred_table: str, local_cols: list[str], remote_cols: list[str]) -> None:
    if not _has_fk(bind, table_name, fk_name):
        op.create_foreign_key(fk_name, table_name, referred_table, local_cols, remote_cols)


def _create_index_if_missing(bind, table_name: str, index_name: str, columns: list[str]) -> None:
    if not _has_index(bind, table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    _add_column_if_missing(bind, "audit_plans", sa.Column("junior_auditor_1_id", sa.Integer(), nullable=True))
    _add_column_if_missing(bind, "audit_plans", sa.Column("junior_auditor_2_id", sa.Integer(), nullable=True))

    _create_index_if_missing(bind, "audit_plans", "ix_audit_plans_junior_auditor_1", ["junior_auditor_1_id"])
    _create_index_if_missing(bind, "audit_plans", "ix_audit_plans_junior_auditor_2", ["junior_auditor_2_id"])

    if dialect != "sqlite":
        _create_fk_if_missing(bind, "audit_plans", "fk_audit_plans_junior_auditor_1_id_users", "users", ["junior_auditor_1_id"], ["id"])
        _create_fk_if_missing(bind, "audit_plans", "fk_audit_plans_junior_auditor_2_id_users", "users", ["junior_auditor_2_id"], ["id"])


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect != "sqlite":
        if _has_fk(bind, "audit_plans", "fk_audit_plans_junior_auditor_2_id_users"):
            op.drop_constraint("fk_audit_plans_junior_auditor_2_id_users", "audit_plans", type_="foreignkey")
        if _has_fk(bind, "audit_plans", "fk_audit_plans_junior_auditor_1_id_users"):
            op.drop_constraint("fk_audit_plans_junior_auditor_1_id_users", "audit_plans", type_="foreignkey")

    if _has_index(bind, "audit_plans", "ix_audit_plans_junior_auditor_2"):
        op.drop_index("ix_audit_plans_junior_auditor_2", table_name="audit_plans")
    if _has_index(bind, "audit_plans", "ix_audit_plans_junior_auditor_1"):
        op.drop_index("ix_audit_plans_junior_auditor_1", table_name="audit_plans")

    if _has_column(bind, "audit_plans", "junior_auditor_2_id"):
        op.drop_column("audit_plans", "junior_auditor_2_id")
    if _has_column(bind, "audit_plans", "junior_auditor_1_id"):
        op.drop_column("audit_plans", "junior_auditor_1_id")
