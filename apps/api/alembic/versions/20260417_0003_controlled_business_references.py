"""controlled business reference generation

Revision ID: 20260417_0003
Revises: 20260411_0002
Create Date: 2026-04-17 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260417_0003"
down_revision = "20260416_0003"
branch_labels = None
depends_on = None


def _has_index(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION next_business_ref(p_entity_name TEXT, p_prefix TEXT, p_ref_year INTEGER, p_pad_length INTEGER DEFAULT 4)
            RETURNS TEXT AS $$
            DECLARE
                v_next INTEGER;
            BEGIN
                INSERT INTO business_reference_counters (entity_name, ref_year, last_value, created_at, updated_at)
                VALUES (p_entity_name, p_ref_year, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (entity_name, ref_year)
                DO UPDATE SET
                    last_value = business_reference_counters.last_value + 1,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING last_value INTO v_next;

                RETURN format('%s-%s-%s', p_prefix, p_ref_year, lpad(v_next::text, p_pad_length, '0'));
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            INSERT INTO business_reference_counters (entity_name, ref_year, last_value, created_at, updated_at)
            SELECT 'audit_number', ref_year, max(ref_number), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM (
                SELECT (regexp_match(audit_number, '^AUD-(\\d{4})-(\\d+)$'))[1]::INTEGER AS ref_year,
                       (regexp_match(audit_number, '^AUD-(\\d{4})-(\\d+)$'))[2]::INTEGER AS ref_number
                FROM audit_plans
                WHERE audit_number ~ '^AUD-\\d{4}-\\d+$'
                UNION ALL
                SELECT (regexp_match(audit_number, '^AUD-(\\d{4})-(\\d+)$'))[1]::INTEGER AS ref_year,
                       (regexp_match(audit_number, '^AUD-(\\d{4})-(\\d+)$'))[2]::INTEGER AS ref_number
                FROM audits
                WHERE audit_number ~ '^AUD-\\d{4}-\\d+$'
            ) refs
            GROUP BY ref_year
            ON CONFLICT (entity_name, ref_year)
            DO UPDATE SET
                last_value = GREATEST(business_reference_counters.last_value, EXCLUDED.last_value),
                updated_at = CURRENT_TIMESTAMP;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_audit_plan_number()
            RETURNS trigger AS $$
            BEGIN
                NEW.audit_number := next_business_ref(
                    'audit_number',
                    'AUD',
                    COALESCE(EXTRACT(YEAR FROM NEW.start_date)::INTEGER, EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER),
                    4
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_audit_number()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.audit_plan_id IS NOT NULL THEN
                    SELECT audit_number INTO NEW.audit_number
                    FROM audit_plans
                    WHERE id = NEW.audit_plan_id;
                END IF;

                IF NEW.audit_number IS NULL OR btrim(NEW.audit_number) = '' THEN
                    NEW.audit_number := next_business_ref(
                        'audit_number',
                        'AUD',
                        COALESCE(EXTRACT(YEAR FROM NEW.start_date)::INTEGER, EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER),
                        4
                    );
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_action_plan_references()
            RETURNS trigger AS $$
            BEGIN
                SELECT audit_number INTO NEW.audit_number
                FROM audits
                WHERE id = NEW.audit_id;

                NEW.action_plan_id := next_business_ref('action_plan', 'ACT', EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 4);
                NEW.observation_number := next_business_ref('observation', 'OBS', EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 4);
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            UPDATE action_plans
            SET observation_number = next_business_ref('observation', 'OBS', EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 4)
            WHERE observation_number IS NULL OR btrim(observation_number) = '';
            """
        )

    if not _has_index(bind, "action_plans", "ix_action_plans_observation_number"):
        op.create_index("ix_action_plans_observation_number", "action_plans", ["observation_number"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if _has_index(bind, "action_plans", "ix_action_plans_observation_number"):
        op.drop_index("ix_action_plans_observation_number", table_name="action_plans")

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_audit_plan_number()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.audit_number IS NULL OR btrim(NEW.audit_number) = '' THEN
                    NEW.audit_number := next_business_ref('audit_plan', 'AUD', COALESCE(EXTRACT(YEAR FROM NEW.start_date)::INTEGER, EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER), 4);
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_audit_number()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.audit_number IS NULL OR btrim(NEW.audit_number) = '' THEN
                    IF NEW.audit_plan_id IS NOT NULL THEN
                        SELECT audit_number INTO NEW.audit_number
                        FROM audit_plans
                        WHERE id = NEW.audit_plan_id;
                    END IF;
                    IF NEW.audit_number IS NULL OR btrim(NEW.audit_number) = '' THEN
                        NEW.audit_number := next_business_ref('audit', 'AUD', COALESCE(EXTRACT(YEAR FROM NEW.start_date)::INTEGER, EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER), 4);
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION generate_action_plan_references()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.audit_number IS NULL OR btrim(NEW.audit_number) = '' THEN
                    SELECT audit_number INTO NEW.audit_number
                    FROM audits
                    WHERE id = NEW.audit_id;
                END IF;
                IF NEW.action_plan_id IS NULL OR btrim(NEW.action_plan_id) = '' THEN
                    NEW.action_plan_id := next_business_ref('action_plan', 'ACT', EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 4);
                END IF;
                IF NEW.observation_number IS NULL OR btrim(NEW.observation_number) = '' THEN
                    NEW.observation_number := next_business_ref('observation', 'OBS', EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 4);
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
