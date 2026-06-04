"""engagement planning and platform foundations

Revision ID: 20260424_0009
Revises: 20260421_0008
Create Date: 2026-04-24 11:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_0009"
down_revision = "20260421_0008"
branch_labels = None
depends_on = None


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _add_actor_fk_columns(bind, table_name: str, *, include_created: bool = True, include_updated: bool = True) -> None:
    if include_created and not _has_column(bind, table_name, "created_by_user_id"):
        op.add_column(table_name, sa.Column("created_by_user_id", sa.Integer(), nullable=True))
        op.create_foreign_key(f"fk_{table_name}_created_by_user_id", table_name, "users", ["created_by_user_id"], ["id"])
        if not _has_index(bind, table_name, f"ix_{table_name}_created_by_user_id"):
            op.create_index(f"ix_{table_name}_created_by_user_id", table_name, ["created_by_user_id"], unique=False)
    if include_updated and not _has_column(bind, table_name, "updated_by_user_id"):
        op.add_column(table_name, sa.Column("updated_by_user_id", sa.Integer(), nullable=True))
        op.create_foreign_key(f"fk_{table_name}_updated_by_user_id", table_name, "users", ["updated_by_user_id"], ["id"])
        if not _has_index(bind, table_name, f"ix_{table_name}_updated_by_user_id"):
            op.create_index(f"ix_{table_name}_updated_by_user_id", table_name, ["updated_by_user_id"], unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    actor_tables = [
        "audit_plans",
        "audits",
        "audit_memberships",
        "audit_activities",
        "observations",
        "action_plans",
        "action_plan_revisions",
        "attachments",
        "activity_logs",
        "notifications",
    ]
    for table_name in actor_tables:
        _add_actor_fk_columns(bind, table_name)
    _add_actor_fk_columns(bind, "management_reviews", include_created=False, include_updated=True)

    op.create_table(
        "audit_events",
        sa.Column("audit_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("event_title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("from_status", sa.String(length=100), nullable=True),
        sa.Column("to_status", sa.String(length=100), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
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
            "event_type IN ('audit_initiated', 'status_changed', 'member_assigned', 'member_removed', 'engagement_created', 'engagement_submitted', 'engagement_approved', 'engagement_rejected', 'engagement_kicked_off')",
            name="ck_audit_events_type_valid",
        ),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_audit_created", "audit_events", ["audit_id", "created_at"], unique=False)
    op.create_index("ix_audit_events_company_location", "audit_events", ["company_id", "location_id"], unique=False)

    op.create_table(
        "notification_outbox",
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False, server_default="in_app"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'dispatched', 'failed')", name="ck_notification_outbox_status_valid"),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_outbox_status_available", "notification_outbox", ["status", "created_at"], unique=False)

    op.create_table(
        "engagement_plans",
        sa.Column("engagement_code", sa.String(length=100), nullable=False),
        sa.Column("audit_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("scope_exclusions", sa.Text(), nullable=True),
        sa.Column("audit_period_from", sa.Date(), nullable=True),
        sa.Column("audit_period_to", sa.Date(), nullable=True),
        sa.Column("kickoff_date", sa.Date(), nullable=True),
        sa.Column("planned_start_date", sa.Date(), nullable=False),
        sa.Column("planned_end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="Draft"),
        sa.Column("lead_auditor_id", sa.Integer(), nullable=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("auditee_spoc_id", sa.Integer(), nullable=True),
        sa.Column("planned_hours", sa.Numeric(10, 2), nullable=True),
        sa.Column("approved_hours", sa.Numeric(10, 2), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('Draft', 'Submitted', 'Approved', 'Rejected', 'Kicked Off')", name="ck_engagement_plans_status_valid"),
        sa.CheckConstraint("planned_end_date >= planned_start_date", name="ck_engagement_plans_date_range"),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["lead_auditor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["auditee_spoc_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("engagement_code"),
    )
    op.create_index("ix_engagement_plans_engagement_code", "engagement_plans", ["engagement_code"], unique=True)
    op.create_index("ix_engagement_plans_audit_status", "engagement_plans", ["audit_id", "status"], unique=False)
    op.create_index("ix_engagement_plans_company_location", "engagement_plans", ["company_id", "location_id"], unique=False)

    op.create_table(
        "engagement_kickoff_checklists",
        sa.Column("engagement_plan_id", sa.Integer(), nullable=False),
        sa.Column("check_item", sa.String(length=255), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["engagement_plan_id"], ["engagement_plans.id"]),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_engagement_kickoff_checklists_plan_completed", "engagement_kickoff_checklists", ["engagement_plan_id", "is_completed"], unique=False)

    op.create_table(
        "engagement_resources",
        sa.Column("engagement_plan_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_in_engagement", sa.String(length=100), nullable=False),
        sa.Column("planned_hours", sa.Numeric(10, 2), nullable=True),
        sa.Column("approved_hours", sa.Numeric(10, 2), nullable=True),
        sa.Column("actual_hours", sa.Numeric(10, 2), nullable=True),
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
            "role_in_engagement IN ('Lead Auditor', 'Reviewer', 'Junior Auditor', 'Audit Support', 'Auditee SPOC', 'Observer')",
            name="ck_engagement_resources_role_valid",
        ),
        sa.ForeignKeyConstraint(["engagement_plan_id"], ["engagement_plans.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_engagement_resources_plan_user", "engagement_resources", ["engagement_plan_id", "user_id"], unique=False)

    op.create_table(
        "engagement_documents",
        sa.Column("engagement_plan_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("is_latest", sa.Boolean(), nullable=False, server_default=sa.true()),
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
            "document_type IN ('Engagement Letter', 'Scope Memo', 'Kickoff Minutes', 'Resource Plan', 'Budget Workbook', 'Other')",
            name="ck_engagement_documents_type_valid",
        ),
        sa.ForeignKeyConstraint(["engagement_plan_id"], ["engagement_plans.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["attachments.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_engagement_documents_plan_type_latest", "engagement_documents", ["engagement_plan_id", "document_type", "is_latest"], unique=False)

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_engagement_plan_code()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.engagement_code IS NULL OR btrim(NEW.engagement_code) = '' THEN
                    NEW.engagement_code := next_business_ref(
                        'engagement_plan',
                        'ENG',
                        COALESCE(EXTRACT(YEAR FROM NEW.planned_start_date)::INTEGER, EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER),
                        4
                    );
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute("DROP TRIGGER IF EXISTS trg_generate_engagement_plan_code ON engagement_plans;")
        op.execute(
            """
            CREATE TRIGGER trg_generate_engagement_plan_code
            BEFORE INSERT ON engagement_plans
            FOR EACH ROW
            EXECUTE FUNCTION generate_engagement_plan_code();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_generate_engagement_plan_code ON engagement_plans;")
        op.execute("DROP FUNCTION IF EXISTS generate_engagement_plan_code();")

    for index_name, table_name in [
        ("ix_engagement_documents_plan_type_latest", "engagement_documents"),
        ("ix_engagement_resources_plan_user", "engagement_resources"),
        ("ix_engagement_kickoff_checklists_plan_completed", "engagement_kickoff_checklists"),
        ("ix_engagement_plans_company_location", "engagement_plans"),
        ("ix_engagement_plans_audit_status", "engagement_plans"),
        ("ix_engagement_plans_engagement_code", "engagement_plans"),
        ("ix_notification_outbox_status_available", "notification_outbox"),
        ("ix_audit_events_company_location", "audit_events"),
        ("ix_audit_events_audit_created", "audit_events"),
    ]:
        if _has_index(bind, table_name, index_name):
            op.drop_index(index_name, table_name=table_name)

    for table_name in [
        "engagement_documents",
        "engagement_resources",
        "engagement_kickoff_checklists",
        "engagement_plans",
        "notification_outbox",
        "audit_events",
    ]:
        op.drop_table(table_name)

    actor_tables = [
        "notifications",
        "activity_logs",
        "attachments",
        "action_plan_revisions",
        "action_plans",
        "observations",
        "audit_activities",
        "audit_memberships",
        "audits",
        "audit_plans",
    ]
    for table_name in actor_tables:
        if _has_index(bind, table_name, f"ix_{table_name}_updated_by_user_id"):
            op.drop_index(f"ix_{table_name}_updated_by_user_id", table_name=table_name)
        if _has_column(bind, table_name, "updated_by_user_id"):
            op.drop_constraint(f"fk_{table_name}_updated_by_user_id", table_name, type_="foreignkey")
            op.drop_column(table_name, "updated_by_user_id")
        if _has_index(bind, table_name, f"ix_{table_name}_created_by_user_id"):
            op.drop_index(f"ix_{table_name}_created_by_user_id", table_name=table_name)
        if _has_column(bind, table_name, "created_by_user_id"):
            op.drop_constraint(f"fk_{table_name}_created_by_user_id", table_name, type_="foreignkey")
            op.drop_column(table_name, "created_by_user_id")

    if _has_index(bind, "management_reviews", "ix_management_reviews_updated_by_user_id"):
        op.drop_index("ix_management_reviews_updated_by_user_id", table_name="management_reviews")
    if _has_column(bind, "management_reviews", "updated_by_user_id"):
        op.drop_constraint("fk_management_reviews_updated_by_user_id", "management_reviews", type_="foreignkey")
        op.drop_column("management_reviews", "updated_by_user_id")
