"""add auditee master and assignment lookup linkage

Revision ID: 20260428_0013
Revises: 20260424_0012
Create Date: 2026-04-28 11:30:00
"""

from __future__ import annotations

from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


revision = "20260428_0013"
down_revision = "20260424_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auditees",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True),
        sa.Column("auditee_code", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("designation", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("linked_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_auditees_auditee_code", "auditees", ["auditee_code"], unique=True)
    op.create_index("ix_auditees_full_name", "auditees", ["full_name"], unique=False)
    op.create_index("ix_auditees_email", "auditees", ["email"], unique=False)
    op.create_index("ix_auditees_linked_user_id", "auditees", ["linked_user_id"], unique=True)
    op.create_index("ix_auditees_created_by_user_id", "auditees", ["created_by_user_id"], unique=False)
    op.create_index("ix_auditees_updated_by_user_id", "auditees", ["updated_by_user_id"], unique=False)

    op.add_column("audits", sa.Column("auditee_spoc_auditee_id", sa.Integer(), nullable=True))
    op.create_index("ix_audits_auditee_spoc_auditee_id", "audits", ["auditee_spoc_auditee_id"], unique=False)
    op.create_foreign_key(
        "fk_audits_auditee_spoc_auditee_id",
        "audits",
        "auditees",
        ["auditee_spoc_auditee_id"],
        ["id"],
    )

    op.add_column("engagement_plans", sa.Column("auditee_spoc_auditee_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_engagement_plans_auditee_spoc_auditee_id",
        "engagement_plans",
        "auditees",
        ["auditee_spoc_auditee_id"],
        ["id"],
    )

    op.add_column("observations", sa.Column("auditee_id", sa.Integer(), nullable=True))
    op.create_index("ix_observations_auditee_id", "observations", ["auditee_id"], unique=False)
    op.create_foreign_key(
        "fk_observations_auditee_id",
        "observations",
        "auditees",
        ["auditee_id"],
        ["id"],
    )

    bind = op.get_bind()
    now = datetime.now(UTC)

    user_rows = bind.execute(
        sa.text(
            """
            SELECT DISTINCT
                u.id AS user_id,
                u.full_name,
                u.email,
                u.phone,
                u.company_id,
                u.location_id,
                d.title AS designation_title
            FROM users u
            LEFT JOIN designations d ON d.id = u.designation_id
            WHERE u.is_deleted = false
              AND u.id IN (
                    SELECT auditee_user_id FROM observations WHERE auditee_user_id IS NOT NULL
                    UNION
                    SELECT auditee_spoc_user_id FROM audits WHERE auditee_spoc_user_id IS NOT NULL
                    UNION
                    SELECT auditee_spoc_id FROM engagement_plans WHERE auditee_spoc_id IS NOT NULL
              )
            ORDER BY u.id
            """
        )
    ).mappings()

    for row in user_rows:
        existing = bind.execute(
            sa.text("SELECT id FROM auditees WHERE linked_user_id = :linked_user_id"),
            {"linked_user_id": row["user_id"]},
        ).scalar()
        if existing:
            continue
        bind.execute(
            sa.text(
                """
                INSERT INTO auditees (
                    auditee_code,
                    full_name,
                    email,
                    phone,
                    designation,
                    department,
                    company_id,
                    location_id,
                    linked_user_id,
                    created_by_user_id,
                    updated_by_user_id,
                    is_active,
                    created_at,
                    updated_at,
                    created_by,
                    updated_by,
                    is_deleted,
                    deleted_at
                ) VALUES (
                    :auditee_code,
                    :full_name,
                    :email,
                    :phone,
                    :designation,
                    NULL,
                    :company_id,
                    :location_id,
                    :linked_user_id,
                    :created_by_user_id,
                    :updated_by_user_id,
                    true,
                    :created_at,
                    :updated_at,
                    :created_by,
                    :updated_by,
                    false,
                    NULL
                )
                """
            ),
            {
                "auditee_code": f"AUDT-{int(row['user_id']):04d}",
                "full_name": row["full_name"],
                "email": row["email"],
                "phone": row["phone"],
                "designation": row["designation_title"],
                "company_id": row["company_id"],
                "location_id": row["location_id"],
                "linked_user_id": row["user_id"],
                "created_by_user_id": row["user_id"],
                "updated_by_user_id": row["user_id"],
                "created_at": now,
                "updated_at": now,
                "created_by": "auditee_master_backfill",
                "updated_by": "auditee_master_backfill",
            },
        )

    bind.execute(
        sa.text(
            """
            UPDATE audits a
            SET auditee_spoc_auditee_id = ad.id
            FROM auditees ad
            WHERE a.auditee_spoc_user_id = ad.linked_user_id
              AND a.auditee_spoc_user_id IS NOT NULL
              AND a.auditee_spoc_auditee_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE engagement_plans ep
            SET auditee_spoc_auditee_id = ad.id
            FROM auditees ad
            WHERE ep.auditee_spoc_id = ad.linked_user_id
              AND ep.auditee_spoc_id IS NOT NULL
              AND ep.auditee_spoc_auditee_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE observations o
            SET auditee_id = ad.id
            FROM auditees ad
            WHERE o.auditee_user_id = ad.linked_user_id
              AND o.auditee_user_id IS NOT NULL
              AND o.auditee_id IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_observations_auditee_id", "observations", type_="foreignkey")
    op.drop_index("ix_observations_auditee_id", table_name="observations")
    op.drop_column("observations", "auditee_id")

    op.drop_constraint("fk_engagement_plans_auditee_spoc_auditee_id", "engagement_plans", type_="foreignkey")
    op.drop_column("engagement_plans", "auditee_spoc_auditee_id")

    op.drop_constraint("fk_audits_auditee_spoc_auditee_id", "audits", type_="foreignkey")
    op.drop_index("ix_audits_auditee_spoc_auditee_id", table_name="audits")
    op.drop_column("audits", "auditee_spoc_auditee_id")

    op.drop_index("ix_auditees_updated_by_user_id", table_name="auditees")
    op.drop_index("ix_auditees_created_by_user_id", table_name="auditees")
    op.drop_index("ix_auditees_linked_user_id", table_name="auditees")
    op.drop_index("ix_auditees_email", table_name="auditees")
    op.drop_index("ix_auditees_full_name", table_name="auditees")
    op.drop_index("ix_auditees_auditee_code", table_name="auditees")
    op.drop_table("auditees")
