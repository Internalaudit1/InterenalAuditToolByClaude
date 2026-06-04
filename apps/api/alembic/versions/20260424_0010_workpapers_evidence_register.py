"""workpapers and evidence register

Revision ID: 20260424_0010
Revises: 20260424_0009
Create Date: 2026-04-24 15:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_0010"
down_revision = "20260424_0009"
branch_labels = None
depends_on = None


def _has_index(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.drop_constraint("ck_audit_events_type_valid", "audit_events", type_="check")
        op.create_check_constraint(
            "ck_audit_events_type_valid",
            "audit_events",
            "event_type IN ('audit_initiated', 'status_changed', 'member_assigned', 'member_removed', 'engagement_created', 'engagement_submitted', 'engagement_approved', 'engagement_rejected', 'engagement_kicked_off', 'workpaper_created', 'workpaper_submitted', 'workpaper_reviewed', 'workpaper_approved', 'workpaper_locked', 'evidence_registered', 'evidence_linked')",
        )

    op.create_table(
        "workpapers",
        sa.Column("workpaper_code", sa.String(length=100), nullable=False),
        sa.Column("audit_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=True),
        sa.Column("observation_id", sa.Integer(), nullable=True),
        sa.Column("test_procedure_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("folder_path", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="Draft"),
        sa.Column("current_version_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewer_user_id", sa.Integer(), nullable=True),
        sa.Column("signoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('Draft', 'Submitted for Review', 'Reviewed', 'Approved', 'Locked')", name="ck_workpapers_status_valid"),
        sa.CheckConstraint("current_version_no >= 0", name="ck_workpapers_version_non_negative"),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["activity_id"], ["audit_activities.id"]),
        sa.ForeignKeyConstraint(["observation_id"], ["observations.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workpaper_code"),
    )
    op.create_index("ix_workpapers_workpaper_code", "workpapers", ["workpaper_code"], unique=True)
    op.create_index("ix_workpapers_audit_id", "workpapers", ["audit_id"], unique=False)
    op.create_index("ix_workpapers_company_location", "workpapers", ["company_id", "location_id"], unique=False)
    op.create_index("ix_workpapers_audit_activity_status", "workpapers", ["audit_id", "activity_id", "status"], unique=False)

    op.create_table(
        "workpaper_versions",
        sa.Column("workpaper_id", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hash_checksum", sa.String(length=128), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workpaper_id"], ["workpapers.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["attachments.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workpaper_id", "version_no", name="uq_workpaper_versions_workpaper_version"),
    )
    op.create_index("ix_workpaper_versions_workpaper_uploaded", "workpaper_versions", ["workpaper_id", "uploaded_at"], unique=False)

    op.create_table(
        "workpaper_reviews",
        sa.Column("workpaper_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_user_id", sa.Integer(), nullable=True),
        sa.Column("review_status", sa.String(length=50), nullable=False),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("review_status IN ('Reviewed', 'Approved', 'Locked')", name="ck_workpaper_reviews_status_valid"),
        sa.ForeignKeyConstraint(["workpaper_id"], ["workpapers.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workpaper_reviews_workpaper_reviewed", "workpaper_reviews", ["workpaper_id", "reviewed_at"], unique=False)

    op.create_table(
        "evidence_register",
        sa.Column("evidence_code", sa.String(length=100), nullable=False),
        sa.Column("audit_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("evidence_description", sa.Text(), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("collected_by_user_id", sa.Integer(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidentiality_level", sa.String(length=50), nullable=False, server_default="Internal"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "confidentiality_level IN ('Internal', 'Confidential', 'Restricted', 'Highly Restricted')",
            name="ck_evidence_register_confidentiality_valid",
        ),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["activity_id"], ["audit_activities.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["attachments.id"]),
        sa.ForeignKeyConstraint(["collected_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_code"),
    )
    op.create_index("ix_evidence_register_evidence_code", "evidence_register", ["evidence_code"], unique=True)
    op.create_index("ix_evidence_register_audit_activity", "evidence_register", ["audit_id", "activity_id"], unique=False)
    op.create_index("ix_evidence_register_company_location", "evidence_register", ["company_id", "location_id"], unique=False)

    op.create_table(
        "evidence_links",
        sa.Column("evidence_id", sa.Integer(), nullable=False),
        sa.Column("linked_module", sa.String(length=50), nullable=False),
        sa.Column("linked_record_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("linked_module IN ('workpaper', 'observation', 'test_procedure')", name="ck_evidence_links_module_valid"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_register.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_id", "linked_module", "linked_record_id", name="uq_evidence_links_unique_target"),
    )
    op.create_index("ix_evidence_links_module_record", "evidence_links", ["linked_module", "linked_record_id"], unique=False)

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_workpaper_code()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.workpaper_code IS NULL OR btrim(NEW.workpaper_code) = '' THEN
                    NEW.workpaper_code := next_business_ref('workpaper', 'WP', EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 4);
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute("DROP TRIGGER IF EXISTS trg_generate_workpaper_code ON workpapers;")
        op.execute(
            """
            CREATE TRIGGER trg_generate_workpaper_code
            BEFORE INSERT ON workpapers
            FOR EACH ROW
            EXECUTE FUNCTION generate_workpaper_code();
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_evidence_register_code()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.evidence_code IS NULL OR btrim(NEW.evidence_code) = '' THEN
                    NEW.evidence_code := next_business_ref('evidence_register', 'EVR', EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 4);
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute("DROP TRIGGER IF EXISTS trg_generate_evidence_register_code ON evidence_register;")
        op.execute(
            """
            CREATE TRIGGER trg_generate_evidence_register_code
            BEFORE INSERT ON evidence_register
            FOR EACH ROW
            EXECUTE FUNCTION generate_evidence_register_code();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_generate_evidence_register_code ON evidence_register;")
        op.execute("DROP FUNCTION IF EXISTS generate_evidence_register_code();")
        op.execute("DROP TRIGGER IF EXISTS trg_generate_workpaper_code ON workpapers;")
        op.execute("DROP FUNCTION IF EXISTS generate_workpaper_code();")

    for index_name, table_name in [
        ("ix_evidence_links_module_record", "evidence_links"),
        ("ix_evidence_register_company_location", "evidence_register"),
        ("ix_evidence_register_audit_activity", "evidence_register"),
        ("ix_evidence_register_evidence_code", "evidence_register"),
        ("ix_workpaper_reviews_workpaper_reviewed", "workpaper_reviews"),
        ("ix_workpaper_versions_workpaper_uploaded", "workpaper_versions"),
        ("ix_workpapers_audit_activity_status", "workpapers"),
        ("ix_workpapers_company_location", "workpapers"),
        ("ix_workpapers_audit_id", "workpapers"),
        ("ix_workpapers_workpaper_code", "workpapers"),
    ]:
        if _has_index(bind, table_name, index_name):
            op.drop_index(index_name, table_name=table_name)

    op.drop_table("evidence_links")
    op.drop_table("evidence_register")
    op.drop_table("workpaper_reviews")
    op.drop_table("workpaper_versions")
    op.drop_table("workpapers")

    if dialect == "postgresql":
        op.drop_constraint("ck_audit_events_type_valid", "audit_events", type_="check")
        op.create_check_constraint(
            "ck_audit_events_type_valid",
            "audit_events",
            "event_type IN ('audit_initiated', 'status_changed', 'member_assigned', 'member_removed', 'engagement_created', 'engagement_submitted', 'engagement_approved', 'engagement_rejected', 'engagement_kicked_off')",
        )
