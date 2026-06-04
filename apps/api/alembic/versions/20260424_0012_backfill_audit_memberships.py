"""backfill audit memberships for existing audits

Revision ID: 20260424_0012
Revises: 20260424_0011
Create Date: 2026-04-24 22:05:00
"""

from __future__ import annotations

from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


revision = "20260424_0012"
down_revision = "20260424_0011"
branch_labels = None
depends_on = None


BACKFILL_ACTOR = "audit_membership_backfill"


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(UTC)

    rows = bind.execute(
        sa.text(
            """
            SELECT
                a.id AS audit_id,
                a.audit_owner_id,
                a.reviewer_user_id,
                a.auditee_spoc_user_id,
                a.created_by,
                a.updated_by,
                a.created_by_user_id,
                a.updated_by_user_id,
                ap.junior_auditor_1_id,
                ap.junior_auditor_2_id
            FROM audits a
            LEFT JOIN audit_plans ap ON ap.id = a.audit_plan_id
            WHERE a.is_deleted = false
            """
        )
    ).mappings()

    for row in rows:
        candidates: list[tuple[int, str]] = []
        if row["audit_owner_id"]:
            candidates.append((row["audit_owner_id"], "lead_auditor"))
        if row["reviewer_user_id"]:
            candidates.append((row["reviewer_user_id"], "reviewer"))
        if row["auditee_spoc_user_id"]:
            candidates.append((row["auditee_spoc_user_id"], "auditee_spoc"))
        for junior_key in ("junior_auditor_1_id", "junior_auditor_2_id"):
            if row[junior_key]:
                candidates.append((row[junior_key], "junior_auditor"))

        for user_id, role_on_audit in candidates:
            existing = bind.execute(
                sa.text(
                    """
                    SELECT id, is_deleted
                    FROM audit_memberships
                    WHERE audit_id = :audit_id
                      AND user_id = :user_id
                      AND role_on_audit = :role_on_audit
                    """
                ),
                {
                    "audit_id": row["audit_id"],
                    "user_id": user_id,
                    "role_on_audit": role_on_audit,
                },
            ).mappings().first()

            created_by = row["created_by"] or BACKFILL_ACTOR
            updated_by = row["updated_by"] or BACKFILL_ACTOR
            created_by_user_id = row["created_by_user_id"]
            updated_by_user_id = row["updated_by_user_id"]

            if existing:
                if existing["is_deleted"]:
                    bind.execute(
                        sa.text(
                            """
                            UPDATE audit_memberships
                            SET
                                is_deleted = false,
                                deleted_at = NULL,
                                updated_at = :updated_at,
                                updated_by = :updated_by,
                                updated_by_user_id = :updated_by_user_id
                            WHERE id = :id
                            """
                        ),
                        {
                            "id": existing["id"],
                            "updated_at": now,
                            "updated_by": updated_by,
                            "updated_by_user_id": updated_by_user_id,
                        },
                    )
                continue

            bind.execute(
                sa.text(
                    """
                    INSERT INTO audit_memberships (
                        audit_id,
                        user_id,
                        role_on_audit,
                        created_at,
                        updated_at,
                        created_by,
                        updated_by,
                        is_deleted,
                        deleted_at,
                        created_by_user_id,
                        updated_by_user_id
                    ) VALUES (
                        :audit_id,
                        :user_id,
                        :role_on_audit,
                        :created_at,
                        :updated_at,
                        :created_by,
                        :updated_by,
                        false,
                        NULL,
                        :created_by_user_id,
                        :updated_by_user_id
                    )
                    """
                ),
                {
                    "audit_id": row["audit_id"],
                    "user_id": user_id,
                    "role_on_audit": role_on_audit,
                    "created_at": now,
                    "updated_at": now,
                    "created_by": created_by,
                    "updated_by": updated_by,
                    "created_by_user_id": created_by_user_id,
                    "updated_by_user_id": updated_by_user_id,
                },
            )


def downgrade() -> None:
    # Data backfill only. Existing memberships should remain in place.
    pass
