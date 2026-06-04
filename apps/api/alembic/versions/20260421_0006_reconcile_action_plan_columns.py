"""reconcile action plan columns with ORM model

Revision ID: 20260421_0006
Revises: 20260421_0005
Create Date: 2026-04-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260421_0006"
down_revision = "20260421_0005"
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


def _set_not_null_when_complete(bind, table_name: str, column_name: str, column_type) -> None:
    missing = bind.scalar(sa.text(f"SELECT count(*) FROM {table_name} WHERE {column_name} IS NULL")) or 0
    if missing == 0:
        op.alter_column(table_name, column_name, existing_type=column_type, nullable=False)


def upgrade() -> None:
    bind = op.get_bind()

    _add_column_if_missing(bind, "action_plans", sa.Column("root_cause_id", sa.Integer(), nullable=True))
    _add_column_if_missing(bind, "action_plans", sa.Column("observation_heading", sa.String(length=255), nullable=True))
    _add_column_if_missing(bind, "action_plans", sa.Column("observation_grading_id", sa.Integer(), nullable=True))
    _add_column_if_missing(bind, "action_plans", sa.Column("detailed_observation", sa.Text(), nullable=True))
    _add_column_if_missing(bind, "action_plans", sa.Column("risk_type_id", sa.Integer(), nullable=True))

    default_grading_id = bind.scalar(sa.text("SELECT id FROM observation_gradings WHERE is_deleted IS false ORDER BY id LIMIT 1"))
    default_risk_type_id = bind.scalar(sa.text("SELECT id FROM risk_types WHERE is_deleted IS false ORDER BY id LIMIT 1"))

    op.execute(
        sa.text(
            """
            UPDATE action_plans
            SET observation_heading = COALESCE(NULLIF(observation_heading, ''), concat('Legacy observation ', id)),
                detailed_observation = COALESCE(detailed_observation, management_response, agreed_action_plan)
            WHERE observation_heading IS NULL OR btrim(observation_heading) = '' OR detailed_observation IS NULL
            """
        )
    )
    if default_grading_id is not None:
        op.execute(
            sa.text("UPDATE action_plans SET observation_grading_id = :default_id WHERE observation_grading_id IS NULL")
            .bindparams(default_id=default_grading_id)
        )
    if default_risk_type_id is not None:
        op.execute(
            sa.text("UPDATE action_plans SET risk_type_id = :default_id WHERE risk_type_id IS NULL")
            .bindparams(default_id=default_risk_type_id)
        )

    _create_fk_if_missing(bind, "action_plans", "fk_action_plans_root_cause_id_root_causes", "root_causes", ["root_cause_id"], ["id"])
    _create_fk_if_missing(bind, "action_plans", "fk_action_plans_observation_grading_id_observation_gradings", "observation_gradings", ["observation_grading_id"], ["id"])
    _create_fk_if_missing(bind, "action_plans", "fk_action_plans_risk_type_id_risk_types", "risk_types", ["risk_type_id"], ["id"])
    _create_index_if_missing(bind, "action_plans", "ix_action_plans_root_cause_id", ["root_cause_id"])
    _create_index_if_missing(bind, "action_plans", "ix_action_plans_observation_grading_id", ["observation_grading_id"])
    _create_index_if_missing(bind, "action_plans", "ix_action_plans_risk_type_id", ["risk_type_id"])

    _set_not_null_when_complete(bind, "action_plans", "observation_heading", sa.String(length=255))
    _set_not_null_when_complete(bind, "action_plans", "observation_grading_id", sa.Integer())
    _set_not_null_when_complete(bind, "action_plans", "risk_type_id", sa.Integer())


def downgrade() -> None:
    bind = op.get_bind()
    for index_name in ("ix_action_plans_risk_type_id", "ix_action_plans_observation_grading_id", "ix_action_plans_root_cause_id"):
        if _has_index(bind, "action_plans", index_name):
            op.drop_index(index_name, table_name="action_plans")
    for fk_name in (
        "fk_action_plans_risk_type_id_risk_types",
        "fk_action_plans_observation_grading_id_observation_gradings",
        "fk_action_plans_root_cause_id_root_causes",
    ):
        if _has_fk(bind, "action_plans", fk_name):
            op.drop_constraint(fk_name, "action_plans", type_="foreignkey")
    for column_name in ("risk_type_id", "detailed_observation", "observation_grading_id", "observation_heading", "root_cause_id"):
        if _has_column(bind, "action_plans", column_name):
            op.drop_column("action_plans", column_name)
