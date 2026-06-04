"""remove unused profit center code fields

Revision ID: 20260424_0011
Revises: 20260424_0010
Create Date: 2026-04-24 18:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_0011"
down_revision = "20260424_0010"
branch_labels = None
depends_on = None


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if _has_index(bind, "locations", "ix_locations_company_profit_center"):
        op.drop_index("ix_locations_company_profit_center", table_name="locations")

    if dialect == "sqlite":
        if _has_column(bind, "locations", "profit_center_code"):
            with op.batch_alter_table("locations") as batch_op:
                batch_op.drop_column("profit_center_code")
        if _has_column(bind, "process_location_mappings", "profit_center_code"):
            with op.batch_alter_table("process_location_mappings") as batch_op:
                batch_op.drop_column("profit_center_code")
        return

    if _has_column(bind, "locations", "profit_center_code"):
        op.drop_column("locations", "profit_center_code")
    if _has_column(bind, "process_location_mappings", "profit_center_code"):
        op.drop_column("process_location_mappings", "profit_center_code")


def downgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "locations", "profit_center_code"):
        op.add_column(
            "locations",
            sa.Column("profit_center_code", sa.String(length=100), nullable=False, server_default=""),
        )
    if not _has_index(bind, "locations", "ix_locations_company_profit_center"):
        op.create_index("ix_locations_company_profit_center", "locations", ["company_id", "profit_center_code"], unique=False)
    if not _has_column(bind, "process_location_mappings", "profit_center_code"):
        op.add_column(
            "process_location_mappings",
            sa.Column("profit_center_code", sa.String(length=100), nullable=True),
        )
