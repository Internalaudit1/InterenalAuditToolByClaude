"""role management and management reviews

Revision ID: 20260416_0003
Revises: 20260411_0002
Create Date: 2026-04-16 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260416_0003"
down_revision = "20260411_0002"
branch_labels = None
depends_on = None


PERMISSIONS_BY_ROLE = {
    "super_admin": {
        "dashboard:view",
        "planning:view",
        "planning:manage",
        "planning:delete",
        "audits:view",
        "audits:manage",
        "audits:delete",
        "action_plans:view",
        "action_plans:create",
        "action_plans:respond",
        "action_plans:review",
        "action_plans:delete",
        "reports:view",
        "reports:export",
        "library:view",
        "library:manage",
        "library:delete",
        "masters:view",
        "masters:manage",
        "masters:delete",
        "users:view",
        "users:manage",
        "users:delete",
        "roles:view",
        "roles:manage",
        "activity_logs:view",
        "management_reviews:view",
        "notifications:view",
    },
    "auditor": {
        "dashboard:view",
        "planning:view",
        "planning:manage",
        "planning:delete",
        "audits:view",
        "audits:manage",
        "audits:delete",
        "action_plans:view",
        "action_plans:create",
        "action_plans:review",
        "action_plans:delete",
        "reports:view",
        "reports:export",
        "library:view",
        "library:manage",
        "library:delete",
        "masters:view",
        "masters:manage",
        "masters:delete",
        "users:view",
        "management_reviews:view",
        "notifications:view",
    },
    "head_auditor": {
        "dashboard:view",
        "planning:view",
        "planning:manage",
        "planning:delete",
        "audits:view",
        "audits:manage",
        "audits:delete",
        "action_plans:view",
        "action_plans:create",
        "action_plans:review",
        "action_plans:delete",
        "reports:view",
        "reports:export",
        "library:view",
        "library:manage",
        "library:delete",
        "masters:view",
        "masters:manage",
        "masters:delete",
        "users:view",
        "users:manage",
        "activity_logs:view",
        "management_reviews:view",
        "notifications:view",
    },
    "management": {
        "dashboard:view",
        "planning:view",
        "audits:view",
        "action_plans:view",
        "reports:view",
        "library:view",
        "management_reviews:view",
        "management_reviews:create",
        "notifications:view",
    },
    "auditee": {
        "planning:view",
        "audits:view",
        "action_plans:view",
        "action_plans:respond",
        "reports:view",
        "library:view",
        "masters:view",
        "notifications:view",
    },
}

ROLE_NAMES = {
    "super_admin": "Super Admin",
    "auditor": "Auditor",
    "head_auditor": "Head Auditor",
    "management": "Management",
    "auditee": "Auditee",
}


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _has_column(bind, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in sa.inspect(bind).get_columns(table_name))


def _has_index(bind, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in sa.inspect(bind).get_indexes(table_name))


def _has_check_constraint(bind, table_name: str, constraint_name: str) -> bool:
    return any(constraint["name"] == constraint_name for constraint in sa.inspect(bind).get_check_constraints(table_name))


def _seed_roles_and_permissions(bind) -> None:
    metadata = sa.MetaData()
    roles = sa.Table("roles", metadata, autoload_with=bind)
    permissions = sa.Table("permissions", metadata, autoload_with=bind)
    role_permissions = sa.Table("role_permissions", metadata, autoload_with=bind)

    permission_ids: dict[str, int] = {}
    for code in sorted({permission for values in PERMISSIONS_BY_ROLE.values() for permission in values}):
        row = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar_one_or_none()
        if row is None:
            result = bind.execute(
                permissions.insert()
                .values(
                    code=code,
                    description=code.replace(":", " ").title(),
                    created_at=sa.text("CURRENT_TIMESTAMP"),
                    updated_at=sa.text("CURRENT_TIMESTAMP"),
                    created_by="migration",
                    updated_by="migration",
                    is_deleted=False,
                )
                .returning(permissions.c.id)
            )
            row = result.scalar_one()
        permission_ids[code] = int(row)

    role_ids: dict[str, int] = {}
    for code, name in ROLE_NAMES.items():
        row = bind.execute(sa.select(roles.c.id).where(roles.c.code == code)).scalar_one_or_none()
        if row is None:
            result = bind.execute(
                roles.insert()
                .values(
                    code=code,
                    name=name,
                    description=f"{name} role",
                    is_system=True,
                    created_at=sa.text("CURRENT_TIMESTAMP"),
                    updated_at=sa.text("CURRENT_TIMESTAMP"),
                    created_by="migration",
                    updated_by="migration",
                    is_deleted=False,
                )
                .returning(roles.c.id)
            )
            row = result.scalar_one()
        else:
            bind.execute(
                roles.update()
                .where(roles.c.id == row)
                .values(is_system=True, updated_at=sa.text("CURRENT_TIMESTAMP"), updated_by="migration")
            )
        role_ids[code] = int(row)

    for role_code, permission_codes in PERMISSIONS_BY_ROLE.items():
        role_id = role_ids[role_code]
        for permission_code in permission_codes:
            permission_id = permission_ids[permission_code]
            existing = bind.execute(
                sa.select(role_permissions.c.role_id).where(
                    role_permissions.c.role_id == role_id,
                    role_permissions.c.permission_id == permission_id,
                )
            ).scalar_one_or_none()
            if existing is None:
                bind.execute(role_permissions.insert().values(role_id=role_id, permission_id=permission_id))


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if not _has_column(bind, "roles", "is_system"):
        op.add_column("roles", sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()))

    if not _has_table(bind, "management_reviews"):
        op.create_table(
            "management_reviews",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("audit_id", sa.Integer(), sa.ForeignKey("audits.id"), nullable=True),
            sa.Column("action_plan_id", sa.Integer(), sa.ForeignKey("action_plans.id"), nullable=True),
            sa.Column("review_note", sa.Text(), nullable=False),
            sa.Column("review_decision", sa.String(length=50), nullable=False, server_default="Noted"),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("created_by", sa.String(length=255), nullable=True),
            sa.Column("updated_by", sa.String(length=255), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    for table_name, index_name, columns in (
        ("management_reviews", "ix_management_reviews_audit_id", ["audit_id"]),
        ("management_reviews", "ix_management_reviews_action_plan_id", ["action_plan_id"]),
        ("management_reviews", "ix_management_reviews_created_by_user_id", ["created_by_user_id"]),
        ("management_reviews", "ix_management_reviews_audit_created", ["audit_id", "created_at"]),
        ("management_reviews", "ix_management_reviews_action_plan_created", ["action_plan_id", "created_at"]),
    ):
        if not _has_index(bind, table_name, index_name):
            op.create_index(index_name, table_name, columns)

    if dialect != "sqlite":
        if not _has_check_constraint(bind, "management_reviews", "ck_management_reviews_exactly_one_target"):
            op.create_check_constraint(
                "ck_management_reviews_exactly_one_target",
                "management_reviews",
                "((audit_id IS NOT NULL AND action_plan_id IS NULL) OR (audit_id IS NULL AND action_plan_id IS NOT NULL))",
            )
        if not _has_check_constraint(bind, "management_reviews", "ck_management_reviews_decision_valid"):
            op.create_check_constraint(
                "ck_management_reviews_decision_valid",
                "management_reviews",
                "review_decision IN ('Noted', 'Needs Attention', 'Escalated')",
            )

    _seed_roles_and_permissions(bind)


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "management_reviews"):
        op.drop_table("management_reviews")
    if _has_column(bind, "roles", "is_system"):
        op.drop_column("roles", "is_system")
