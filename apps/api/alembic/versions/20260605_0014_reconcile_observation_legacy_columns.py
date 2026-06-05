"""Reconcile legacy observation columns with lifecycle observation model.

Revision ID: 20260605_0014
Revises: 20260428_0013
Create Date: 2026-06-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260605_0014"
down_revision = "20260428_0013"
branch_labels = None
depends_on = None


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "observations", "observation_text"):
        op.add_column("observations", sa.Column("observation_text", sa.Text(), nullable=True))

    if _has_column(bind, "observations", "detailed_observation"):
        op.execute(
            sa.text(
                """
                UPDATE observations
                SET observation_text = COALESCE(observation_text, detailed_observation)
                WHERE observation_text IS NULL
                  AND detailed_observation IS NOT NULL
                """
            )
        )
        op.execute(
            sa.text(
                """
                UPDATE observations
                SET detailed_observation = COALESCE(detailed_observation, observation_text, '')
                WHERE detailed_observation IS NULL
                """
            )
        )
        op.alter_column("observations", "detailed_observation", existing_type=sa.Text(), nullable=True)

    if _has_column(bind, "observations", "auditee_remarks") and _has_column(bind, "observations", "auditee_remark"):
        op.execute(
            sa.text(
                """
                UPDATE observations
                SET auditee_remark = COALESCE(auditee_remark, auditee_remarks)
                WHERE auditee_remark IS NULL
                  AND auditee_remarks IS NOT NULL
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "observations", "detailed_observation"):
        op.execute(
            sa.text(
                """
                UPDATE observations
                SET detailed_observation = COALESCE(detailed_observation, observation_text, '')
                WHERE detailed_observation IS NULL
                """
            )
        )
        op.alter_column("observations", "detailed_observation", existing_type=sa.Text(), nullable=False)
