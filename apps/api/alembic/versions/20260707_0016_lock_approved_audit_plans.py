"""database-level immutability for approved audit plans (PostgreSQL)

Revision ID: 20260707_0016
Revises: 20260707_0015
Create Date: 2026-07-07 12:00:00
"""

from __future__ import annotations

from alembic import op


revision = "20260707_0016"
down_revision = "20260707_0015"
branch_labels = None
depends_on = None

FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION lock_approved_audit_plans()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.approval_status = 'Approved' THEN
        IF (NEW.audit_number IS DISTINCT FROM OLD.audit_number
            OR NEW.audit_name IS DISTINCT FROM OLD.audit_name
            OR NEW.company_id IS DISTINCT FROM OLD.company_id
            OR NEW.location_id IS DISTINCT FROM OLD.location_id
            OR NEW.fiscal_year IS DISTINCT FROM OLD.fiscal_year
            OR NEW.serial_no IS DISTINCT FROM OLD.serial_no
            OR NEW.audit_area IS DISTINCT FROM OLD.audit_area
            OR NEW.caro_status IS DISTINCT FROM OLD.caro_status
            OR NEW.audit_scope_type IS DISTINCT FROM OLD.audit_scope_type
            OR NEW.criticality IS DISTINCT FROM OLD.criticality
            OR NEW.start_date IS DISTINCT FROM OLD.start_date
            OR NEW.end_date IS DISTINCT FROM OLD.end_date
            OR NEW.period_type IS DISTINCT FROM OLD.period_type
            OR NEW.period_value IS DISTINCT FROM OLD.period_value
            OR NEW.quarter IS DISTINCT FROM OLD.quarter
            OR NEW.approval_status IS DISTINCT FROM OLD.approval_status
            OR NEW.is_deleted IS DISTINCT FROM OLD.is_deleted) THEN
            RAISE EXCEPTION 'Audit plan % is approved and locked; only remarks may be updated.', OLD.audit_number
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

TRIGGER_SQL = """
DROP TRIGGER IF EXISTS trg_lock_approved_audit_plans ON audit_plans;
CREATE TRIGGER trg_lock_approved_audit_plans
BEFORE UPDATE ON audit_plans
FOR EACH ROW EXECUTE FUNCTION lock_approved_audit_plans();
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(FUNCTION_SQL)
    op.execute(TRIGGER_SQL)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP TRIGGER IF EXISTS trg_lock_approved_audit_plans ON audit_plans;")
    op.execute("DROP FUNCTION IF EXISTS lock_approved_audit_plans();")
