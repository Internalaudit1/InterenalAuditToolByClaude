"""allow monthly audit period values

Revision ID: 20260421_0008
Revises: 20260421_0007
Create Date: 2026-04-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260421_0008"
down_revision = "20260421_0007"
branch_labels = None
depends_on = None


MONTH_VALUES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _has_constraint(bind, table_name: str, constraint_name: str) -> bool:
    return any(constraint["name"] == constraint_name for constraint in sa.inspect(bind).get_check_constraints(table_name))


def _drop_constraint_if_exists(bind, table_name: str, constraint_name: str) -> None:
    if _has_constraint(bind, table_name, constraint_name):
        op.drop_constraint(constraint_name, table_name, type_="check")


def _add_check(bind, table_name: str, constraint_name: str, expression: str) -> None:
    if _has_constraint(bind, table_name, constraint_name):
        return
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} CHECK ({expression}) NOT VALID"))
    else:
        op.create_check_constraint(constraint_name, table_name, expression)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    bind = op.get_bind()
    monthly_values = _quoted(MONTH_VALUES)
    all_period_values = _quoted((*MONTH_VALUES, "Q1", "Q2", "Q3", "Q4", "H1", "H2", "Full Year"))
    period_type_expr = "period_type IS NULL OR period_type IN ('Monthly', 'Quarterly', 'Half-Yearly', 'Annual')"
    period_value_expr = f"period_value IS NULL OR period_value IN ({all_period_values})"
    period_pair_expr = (
        "period_type IS NULL OR period_value IS NULL OR "
        f"(period_type = 'Monthly' AND period_value IN ({monthly_values})) OR "
        "(period_type = 'Quarterly' AND period_value IN ('Q1', 'Q2', 'Q3', 'Q4')) OR "
        "(period_type = 'Half-Yearly' AND period_value IN ('H1', 'H2')) OR "
        "(period_type = 'Annual' AND period_value = 'Full Year')"
    )

    for table_name in ("audit_plans", "audits"):
        _drop_constraint_if_exists(bind, table_name, f"ck_{table_name}_period_pair_valid")
        _drop_constraint_if_exists(bind, table_name, f"ck_{table_name}_period_value_valid")
        _drop_constraint_if_exists(bind, table_name, f"ck_{table_name}_period_type_valid")
        _add_check(bind, table_name, f"ck_{table_name}_period_type_valid", period_type_expr)
        _add_check(bind, table_name, f"ck_{table_name}_period_value_valid", period_value_expr)
        _add_check(bind, table_name, f"ck_{table_name}_period_pair_valid", period_pair_expr)


def downgrade() -> None:
    bind = op.get_bind()
    period_type_expr = "period_type IS NULL OR period_type IN ('Quarterly', 'Half-Yearly', 'Annual')"
    period_value_expr = "period_value IS NULL OR period_value IN ('Q1', 'Q2', 'Q3', 'Q4', 'H1', 'H2', 'Full Year')"
    period_pair_expr = (
        "period_type IS NULL OR period_value IS NULL OR "
        "(period_type = 'Quarterly' AND period_value IN ('Q1', 'Q2', 'Q3', 'Q4')) OR "
        "(period_type = 'Half-Yearly' AND period_value IN ('H1', 'H2')) OR "
        "(period_type = 'Annual' AND period_value = 'Full Year')"
    )

    for table_name in ("audit_plans", "audits"):
        _drop_constraint_if_exists(bind, table_name, f"ck_{table_name}_period_pair_valid")
        _drop_constraint_if_exists(bind, table_name, f"ck_{table_name}_period_value_valid")
        _drop_constraint_if_exists(bind, table_name, f"ck_{table_name}_period_type_valid")
        _add_check(bind, table_name, f"ck_{table_name}_period_type_valid", period_type_expr)
        _add_check(bind, table_name, f"ck_{table_name}_period_value_valid", period_value_expr)
        _add_check(bind, table_name, f"ck_{table_name}_period_pair_valid", period_pair_expr)
