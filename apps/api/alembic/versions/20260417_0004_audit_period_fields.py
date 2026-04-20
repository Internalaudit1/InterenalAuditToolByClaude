"""audit period type and value fields

Revision ID: 20260417_0004
Revises: 20260417_0003
Create Date: 2026-04-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260417_0004"
down_revision = "20260417_0003"
branch_labels = None
depends_on = None


FISCAL_YEARS = tuple(f"{year}-{year + 1}" for year in range(2025, 2043))


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_constraint(bind, table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(bind)
    constraints = inspector.get_check_constraints(table_name)
    return any(constraint["name"] == constraint_name for constraint in constraints)


def _drop_constraint_if_exists(bind, table_name: str, constraint_name: str) -> None:
    if _has_constraint(bind, table_name, constraint_name):
        op.drop_constraint(constraint_name, table_name, type_="check")


def _add_check_not_valid(bind, table_name: str, constraint_name: str, expression: str) -> None:
    if not _has_constraint(bind, table_name, constraint_name):
        op.execute(sa.text(f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} CHECK ({expression}) NOT VALID"))


def _add_period_columns(bind, table_name: str) -> None:
    if not _has_column(bind, table_name, "period_type"):
        op.add_column(table_name, sa.Column("period_type", sa.String(length=50), nullable=True))
    if not _has_column(bind, table_name, "period_value"):
        op.add_column(table_name, sa.Column("period_value", sa.String(length=50), nullable=True))


def _backfill_periods(table_name: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET
                period_type = CASE
                    WHEN upper(trim(quarter)) IN ('Q1', 'Q2', 'Q3', 'Q4') THEN 'Quarterly'
                    WHEN upper(trim(quarter)) IN ('H1', 'H2') THEN 'Half-Yearly'
                    WHEN lower(trim(quarter)) IN ('full year', 'fullyear', 'annual', 'year') THEN 'Annual'
                    ELSE period_type
                END,
                period_value = CASE
                    WHEN upper(trim(quarter)) IN ('Q1', 'Q2', 'Q3', 'Q4') THEN upper(trim(quarter))
                    WHEN upper(trim(quarter)) IN ('H1', 'H2') THEN upper(trim(quarter))
                    WHEN lower(trim(quarter)) IN ('full year', 'fullyear', 'annual', 'year') THEN 'Full Year'
                    ELSE period_value
                END
            WHERE period_type IS NULL OR period_value IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET fiscal_year = concat(substring(fiscal_year from 1 for 4), '-20', substring(fiscal_year from 6 for 2))
            WHERE fiscal_year ~ '^[0-9]{{4}}-[0-9]{{2}}$'
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    fiscal_year_values = ", ".join(f"'{year}'" for year in FISCAL_YEARS)
    period_type_expr = "period_type IS NULL OR period_type IN ('Quarterly', 'Half-Yearly', 'Annual')"
    period_value_expr = (
        "period_value IS NULL OR period_value IN ('Q1', 'Q2', 'Q3', 'Q4', 'H1', 'H2', 'Full Year')"
    )
    period_pair_expr = (
        "period_type IS NULL OR period_value IS NULL OR "
        "(period_type = 'Quarterly' AND period_value IN ('Q1', 'Q2', 'Q3', 'Q4')) OR "
        "(period_type = 'Half-Yearly' AND period_value IN ('H1', 'H2')) OR "
        "(period_type = 'Annual' AND period_value = 'Full Year')"
    )
    fiscal_year_expr = f"fiscal_year IN ({fiscal_year_values})"

    for table_name in ("audit_plans", "audits"):
        _add_period_columns(bind, table_name)
        _backfill_periods(table_name)
        _add_check_not_valid(bind, table_name, f"ck_{table_name}_period_type_valid", period_type_expr)
        _add_check_not_valid(bind, table_name, f"ck_{table_name}_period_value_valid", period_value_expr)
        _add_check_not_valid(bind, table_name, f"ck_{table_name}_period_pair_valid", period_pair_expr)
        _add_check_not_valid(bind, table_name, f"ck_{table_name}_fiscal_year_valid", fiscal_year_expr)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in ("audits", "audit_plans"):
        _drop_constraint_if_exists(bind, table_name, f"ck_{table_name}_fiscal_year_valid")
        _drop_constraint_if_exists(bind, table_name, f"ck_{table_name}_period_pair_valid")
        _drop_constraint_if_exists(bind, table_name, f"ck_{table_name}_period_value_valid")
        _drop_constraint_if_exists(bind, table_name, f"ck_{table_name}_period_type_valid")
        if _has_column(bind, table_name, "period_value"):
            op.drop_column(table_name, "period_value")
        if _has_column(bind, table_name, "period_type"):
            op.drop_column(table_name, "period_type")
