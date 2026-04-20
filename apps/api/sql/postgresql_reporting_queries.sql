-- Audit-wise open observations
SELECT
    a.audit_number,
    a.audit_name,
    ap.action_plan_id,
    ap.observation_number,
    ap.observation_heading,
    ap.auditor_status,
    ap.auditee_status,
    ap.agreed_timeline
FROM audits AS a
JOIN action_plans AS ap ON ap.audit_id = a.id
WHERE a.is_deleted = FALSE
  AND ap.is_deleted = FALSE
  AND ap.auditor_status <> 'Completed'
ORDER BY a.audit_number, ap.agreed_timeline;

-- Overdue action plans
SELECT
    ap.action_plan_id,
    ap.observation_number,
    ap.audit_number,
    ap.observation_heading,
    ap.agreed_timeline,
    ap.auditor_status,
    ap.auditee_status,
    (CURRENT_DATE - ap.agreed_timeline) AS days_overdue
FROM action_plans AS ap
WHERE ap.is_deleted = FALSE
  AND ap.auditor_status <> 'Completed'
  AND ap.agreed_timeline < CURRENT_DATE
ORDER BY ap.agreed_timeline;

-- Observations by severity
SELECT
    og.code AS grading_code,
    og.name AS grading_name,
    COUNT(*) AS observation_count
FROM action_plans AS ap
JOIN observation_gradings AS og ON og.id = ap.observation_grading_id
WHERE ap.is_deleted = FALSE
GROUP BY og.code, og.name, og.severity_rank
ORDER BY og.severity_rank ASC, og.name;

-- Entity-wise audit status
SELECT
    c.name AS company_name,
    l.location_code,
    l.description AS location_name,
    a.status,
    COUNT(*) AS audit_count
FROM audits AS a
JOIN companies AS c ON c.id = a.company_id
JOIN locations AS l ON l.id = a.location_id
WHERE a.is_deleted = FALSE
GROUP BY c.name, l.location_code, l.description, a.status
ORDER BY c.name, l.location_code, a.status;

-- Closure ageing
SELECT
    ap.action_plan_id,
    ap.observation_number,
    ap.observation_heading,
    ap.created_at,
    ap.completed_at,
    EXTRACT(DAY FROM (ap.completed_at - ap.created_at)) AS closure_age_days
FROM action_plans AS ap
WHERE ap.is_deleted = FALSE
  AND ap.completed_at IS NOT NULL
ORDER BY closure_age_days DESC NULLS LAST;

-- User-wise assigned actions
SELECT
    u.username,
    u.full_name,
    COUNT(*) AS assigned_action_count,
    SUM(CASE WHEN ap.auditor_status = 'Completed' THEN 1 ELSE 0 END) AS completed_count,
    SUM(CASE WHEN ap.auditor_status <> 'Completed' THEN 1 ELSE 0 END) AS open_count
FROM users AS u
JOIN action_plans AS ap ON ap.implementation_owner_user_id = u.id
WHERE u.is_deleted = FALSE
  AND ap.is_deleted = FALSE
GROUP BY u.username, u.full_name
ORDER BY assigned_action_count DESC, u.username;
