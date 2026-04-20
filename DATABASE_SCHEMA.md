# Database Schema Summary

## Identity and Access

- `users`: application users with company, location, and designation links
- `roles`: role master for super admin, auditor, auditee
- `permissions`: atomic permission catalog
- `user_roles`: many-to-many user to role mapping
- `role_permissions`: many-to-many role to permission mapping
- `refresh_tokens`: persistent refresh token records

## Planning and Audit Execution

- `audit_plans`: planned audit universe and scoping records
- `audits`: executable audit lifecycle records
- `process_risk_mappings`: process-level rating inputs by audit plan
- `erm_risks`: ERM risks linked to audit plans
- `business_initiatives`: initiative capture linked to audit plans
- `overall_assessments`: location coverage and overall-risk decisions

## Action Plans

- `action_plans`: main remediation record with split auditor and auditee statuses
- `action_plan_revisions`: immutable revision trail for response cycles and reopen events
- `attachments`: evidence and supporting file metadata
- `business_reference_counters`: PostgreSQL-safe yearly counter store for business reference generation

## Reference and Master Data

- `countries`
- `states`
- `cities`
- `companies`
- `processes`
- `locations`
- `process_location_mappings`
- `risk_types`
- `report_considerations`
- `recommendations`
- `root_causes`
- `impacts`
- `trial_balances`
- `observation_gradings`
- `audit_escalations`
- `designations`
- `control_performance_indicators`
- `task_swap_rules`

## Support Tables

- `knowledge_library_items`: searchable document and template library
- `activity_logs`: audit trail with before and after snapshots
- `notifications`: workflow notifications by user

## Common Design Rules

- Most business tables include:
  - `created_at`
  - `updated_at`
  - `created_by`
  - `updated_by`
  - `is_deleted`
  - `deleted_at`
- Soft delete is available for operational records
- Relationships are normalized for company, location, user, role, and workflow entities
- Master/reference tables also carry `is_active` for safe deactivation without delete

## Business Reference Codes

- `audit_plans.audit_number`: generated as `AUD-YYYY-0001` when omitted
- `audits.audit_number`: copied from linked audit plan when present, otherwise generated as `AUD-YYYY-0001`
- `action_plans.action_plan_id`: generated as `ACT-YYYY-0001` when omitted
- `action_plans.observation_number`: generated as `OBS-YYYY-0001` when omitted
- `action_plan_revisions.response_code`: generated as `MRG-YYYY-0001`
- `attachments.evidence_code`: generated as `EVD-YYYY-0001`
- PostgreSQL uses database functions and triggers for generation; SQLite/test mode uses ORM listeners for compatibility

## PostgreSQL Implementation Files

- Migration: [20260411_0002_postgresql_reference_hardening.py](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/apps/api/alembic/versions/20260411_0002_postgresql_reference_hardening.py)
- Reporting query examples: [postgresql_reporting_queries.sql](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/apps/api/sql/postgresql_reporting_queries.sql)

## Key Relationships

- `audit_plans -> audits` is one-to-one or one-to-zero in this demo
- `audits -> action_plans` is one-to-many
- `action_plans -> action_plan_revisions` is one-to-many
- `companies -> locations` is one-to-many
- `processes -> process_location_mappings` is one-to-many
- `users -> notifications` is one-to-many
- `roles <-> permissions` is many-to-many
- `users <-> roles` is many-to-many
