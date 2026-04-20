# Workflow Notes

## Audit Lifecycle

Statuses:

- `To be Initiated`
- `In Progress`
- `Completed`
- `Overdue`
- `Unplanned`

Rules:

- Audit plans define the planned universe
- Audits track execution lifecycle
- Overdue is derived from date logic when the end date has passed and the audit is not completed
- Unplanned audits can exist outside the formal plan
- Audit history is stored as timeline entries on the audit record

## Action Plan Lifecycle

Statuses:

- `Pending to be initiated`
- `In Progress`
- `Under Review`
- `Completed`
- `Reopened`

### Auditor controls

- Only Auditor or Super Admin can create action plans
- Auditor status is server-owned and cannot be set by Auditee review endpoints
- Reopen increments `revision_count`
- Completion requires auditee response to be in `Under Review` with management response captured

### Auditee controls

- Auditee cannot create action plans
- Auditee can submit:
  - management response
  - agreed action plan
  - implementation remarks
  - evidence attachment references
- Auditee status transitions are restricted:
  - `Pending to be initiated -> In Progress`
  - `In Progress -> Under Review`
  - `Reopened -> In Progress`

### Revision handling

- Every response or reopen can create a revision row
- Revision rows preserve remarks, revised date, optional attachment, and status snapshot
- Auditor review does not overwrite auditee revision history

## Route and Control Improvements

Compared to the observed source tool:

- Dashboard access is role-restricted
- Broken routes are replaced with real pages
- Activity Logs is an actual admin surface
- Initial Data Request is implemented rather than redirected
- Backend authorization protects direct URL access via API enforcement

## Activity Logging

Every important mutation should generate an activity log entry with:

- actor
- role
- module
- entity type
- entity id
- action type
- old values
- new values
- request metadata where available
- correlation ID

