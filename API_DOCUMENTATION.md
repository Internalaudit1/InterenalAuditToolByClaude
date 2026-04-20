# API Documentation

Base URL: `/api/v1`

## Auth

- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`

Example login request:

```json
{
  "username": "auditoruser1",
  "password": "Password@123"
}
```

Example login response:

```json
{
  "access_token": "jwt",
  "refresh_token": "jwt",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 2,
    "username": "auditoruser1",
    "email": "auditor@dia.local",
    "full_name": "Auditor User 1",
    "roles": ["auditor"],
    "permissions": ["action_plans:create", "reports:export"]
  }
}
```

## Dashboard

- `GET /dashboard/summary`

Returns KPI cards plus chart data for:

- audit status summary
- action plan aging
- severity distribution
- location distribution

## Planning

- `GET /planning/process-risk-mappings`
- `POST /planning/process-risk-mappings`
- `PUT /planning/process-risk-mappings/{id}`
- `GET /planning/erm-risks`
- `POST /planning/erm-risks`
- `PUT /planning/erm-risks/{id}`
- `GET /planning/business-initiatives`
- `POST /planning/business-initiatives`
- `PUT /planning/business-initiatives/{id}`
- `GET /planning/overall-assessments`
- `POST /planning/overall-assessments`
- `PUT /planning/overall-assessments/{id}`
- `GET /planning/audit-plans`
- `POST /planning/audit-plans`
- `PUT /planning/audit-plans/{id}`

Supported list parameters:

- `page`
- `page_size`
- `search`
- route-specific filters such as `audit_plan_id`, `company_id`, `location_id`, `quarter`

## Audits

- `GET /audits`
- `GET /audits/{id}`
- `POST /audits`
- `PUT /audits/{id}`

Supported filters:

- `status`
- `quarter`
- `planned_flag`

## Action Plans

- `GET /action-plans`
- `GET /action-plans/summary`
- `GET /action-plans/{id}`
- `POST /action-plans`
- `PUT /action-plans/{id}`
- `POST /action-plans/{id}/response`
- `POST /action-plans/{id}/review`
- `POST /action-plans/{id}/reopen`
- `POST /action-plans/{id}/attachments`
- `GET /action-plans/attachments/{attachment_id}/download`

Example response submission:

```json
{
  "management_response": "Workflow has been configured.",
  "agreed_action_plan": "Deploy maker-checker in ERP.",
  "management_implementation_remarks": "Ready for auditor review.",
  "auditee_status": "Under Review",
  "revised_date": "2026-04-21",
  "attachment_ids": []
}
```

Example auditor review:

```json
{
  "auditor_status": "Completed",
  "auditor_implementation_remarks": "Validated closure evidence."
}
```

## Reports

- `GET /reports`
- `GET /reports/export/excel`
- `GET /reports/export/pdf`

Supported filters:

- `report_type`
- `company_id`
- `location_id`
- `audit_id`
- `quarter`
- `status`
- `criticality`
- `start_date`
- `end_date`

## Knowledge Library

- `GET /knowledge-library`
- `POST /knowledge-library`
- `PUT /knowledge-library/{id}`

Supported filters:

- `item_type`
- `category`
- `search`

## Master Data

Generic resource route pattern:

- `GET /master/{resource}`
- `POST /master/{resource}`
- `PUT /master/{resource}/{id}`

Supported resources:

- `countries`
- `states`
- `cities`
- `companies`
- `processes`
- `locations`
- `process-location-mappings`
- `risk-types`
- `report-considerations`
- `recommendations`
- `root-causes`
- `impacts`
- `trial-balances`
- `observation-gradings`
- `audit-escalations`
- `designations`
- `control-performance-indicators`
- `task-swaps`

## Admin

- `GET /admin/activity-logs`
- `GET /admin/notifications`
- `GET /admin/users`
- `POST /admin/users`
- `PUT /admin/users/{id}`
- `PUT /admin/users/{id}/roles`

## Auth Flow

1. Client calls `POST /auth/login`
2. Access token is sent as `Authorization: Bearer <token>`
3. When access expires, client calls `POST /auth/refresh`
4. Backend permission checks are enforced on every protected route

## Response Notes

- Mutating endpoints write to `activity_logs`
- Export endpoints write export activity records
- Action plan transitions create notifications for affected owners

