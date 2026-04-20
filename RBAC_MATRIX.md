# RBAC Matrix

## Module vs Role

| Module / Capability | Super Admin | Auditor | Auditee |
|---|---|---|---|
| Dashboard | View | View | No |
| Planning lists | View | View | Audit Plans only |
| Planning create / edit | Yes | Yes | No |
| Manage Audits view | Yes | Yes | Yes |
| Manage Audits edit | Yes | Yes | No |
| Action Plan list | Yes | Yes | Yes |
| Create Action Plan | Yes | Yes | No |
| Submit Auditee Response | Yes | Assigned/allowed | Assigned/allowed |
| Auditor Review / Reopen | Yes | Yes | No |
| Reports view | Yes | Yes | Yes |
| Reports export | Yes | Yes | No by default |
| Knowledge Library view | Yes | Yes | Yes |
| Knowledge Library manage | Yes | Yes | No |
| Master Data view | Yes | Yes | Yes |
| Master Data manage | Yes | Yes | No |
| Users view | Yes | Yes | No |
| Users manage | Yes | No | No |
| Activity Logs view | Yes | No | No |
| Notifications view | Yes | Yes | Yes |

## Permission Codes

### Super Admin

- `dashboard:view`
- `planning:view`
- `planning:manage`
- `audits:view`
- `audits:manage`
- `action_plans:view`
- `action_plans:create`
- `action_plans:respond`
- `action_plans:review`
- `reports:view`
- `reports:export`
- `library:view`
- `library:manage`
- `masters:view`
- `masters:manage`
- `users:view`
- `users:manage`
- `activity_logs:view`
- `notifications:view`

### Auditor

- `dashboard:view`
- `planning:view`
- `planning:manage`
- `audits:view`
- `audits:manage`
- `action_plans:view`
- `action_plans:create`
- `action_plans:review`
- `reports:view`
- `reports:export`
- `library:view`
- `library:manage`
- `masters:view`
- `masters:manage`
- `users:view`
- `notifications:view`

### Auditee

- `planning:view`
- `audits:view`
- `action_plans:view`
- `action_plans:respond`
- `reports:view`
- `library:view`
- `masters:view`
- `notifications:view`

