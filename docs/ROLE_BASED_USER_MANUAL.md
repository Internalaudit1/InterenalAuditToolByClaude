# Role-Based User Manual

This manual explains how to use the Internal Audit Management Tool from the perspective of the three main business users:

- Head Auditor
- Auditor / Lead Auditor
- Auditee

It is written against the current working application and its real module structure.

## 1. Before You Start

### 1.1 Understand the role model

There are two different concepts in the tool:

- `System role`
  - examples: `head_auditor`, `auditor`, `auditee`, `super_admin`
- `Audit assignment role`
  - examples: `lead_auditor`, `junior_auditor`, `reviewer`, `auditee_spoc`

Important:

- `Lead Auditor` is not a separate login role by default.
- A user usually logs in as an `auditor`.
- That auditor becomes the `Lead Auditor` for a specific audit when assigned on the Audit Plan and carried into the initiated audit.

### 1.2 High-level workflow

The intended working sequence is:

1. Head Auditor creates or reviews the Audit Plan
2. Head Auditor approves the Audit Plan
3. Head Auditor initiates the audit
4. Assigned Lead Auditor receives access to that audit
5. Lead Auditor starts Engagement Planning
6. Lead Auditor and team execute the audit
7. Auditor raises observations
8. Auditee submits remarks / response
9. Auditor converts accepted items into Action Plans
10. Auditee updates implementation remarks
11. Auditor reviews closure progress

## 2. Module Overview

These are the main modules relevant to day-to-day use:

- `Audit Planning Engine`
  - process risk mapping, ERM risks, initiatives, assessment, audit plans
- `Engagement Planning`
  - engagement plan creation, kickoff, staffing, engagement documents
- `Manage Audits`
  - audit execution view
- `Workpapers`
  - working papers and review flow
- `Evidence Register`
  - evidence capture and linkage
- `My Activities`
  - assigned audit activities
- `Observations`
  - findings / observations during the audit
- `Action Plans`
  - remediation tracking
- `Reports`
  - reporting and exports

## 3. Head Auditor Manual

### 3.1 Main responsibility

The Head Auditor governs planning and initiation. This role is responsible for:

- reviewing and approving Audit Plans
- initiating approved plans into real audits
- ensuring the correct Lead Auditor is assigned before initiation
- monitoring engagement and audit progress

### 3.2 Step-by-step: approve and initiate an audit

1. Log in as a user with `head_auditor` access.
2. Open [Audit Plans](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/apps/web/app/(app)/planning/[section]/page.tsx).
3. Search for the required planned audit.
4. Open or edit the record and confirm these fields are complete:
   - Audit Name
   - Company
   - Location
   - Period Type
   - Period Value
   - Fiscal Year
   - Start Date
   - End Date
   - Criticality
   - Lead Auditor
   - optional Junior Auditor 1
   - optional Junior Auditor 2
5. If the plan is still in `Draft`, click `Submit`.
6. When the plan moves to `Under Review`, click `Approve`.
7. After approval, click `Initiate Audit`.

Expected result:

- a real audit record is created
- the Audit Number is carried into the execution audit
- the assigned Lead Auditor gets access to that audit
- junior auditors from the plan also inherit membership where assigned

### 3.3 What to check after initiation

Open `Manage Audits` and confirm:

- the audit exists
- the correct Audit Number is visible
- the correct Lead Auditor is associated
- the audit is ready for engagement planning

If the Lead Auditor says they cannot see the audit:

- confirm the Audit Plan had a Lead Auditor assigned before initiation
- confirm the audit was actually initiated, not only approved
- ask the auditor to log out and log back in once

### 3.4 What the Head Auditor should not expect

- approving the Audit Plan does not auto-create the engagement plan
- the engagement plan is started separately by the assigned Lead Auditor

## 4. Auditor / Lead Auditor Manual

## 4.1 Main responsibility

The auditor executes the audit. When assigned as `Lead Auditor` for a specific audit, this user is responsible for:

- starting the engagement plan
- defining objective and scope
- kickoff readiness
- assigning resources
- managing workpapers and evidence
- raising observations
- reviewing auditee responses
- creating and tracking action plans

## 4.2 How to know you are the Lead Auditor

You are acting as the Lead Auditor for an audit when:

- the Head Auditor selected your user in the Audit Plan `Lead Auditor` field
- the Head Auditor initiated that approved plan
- the audit now appears in your `Manage Audits` list

### 4.3 Step-by-step: start engagement planning

1. Log in as the assigned auditor.
2. Open [Manage Audits](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/apps/web/app/(app)/audits/page.tsx).
3. Find the audit assigned to you.
4. Click `Start Engagement`.

Expected result:

- you are taken to `Engagement Planning`
- the selected audit is already prefilled
- title, dates, scope starter text, and Lead Auditor mapping are loaded

Alternative path:

1. Open [Engagement Planning](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/apps/web/app/(app)/engagement-plans/page.tsx)
2. Use the `Select Audit` dropdown
3. Choose one of your assigned audits

If no audit appears in `Select Audit`, the most common reasons are:

- the audit has not been initiated yet
- you were not assigned as Lead Auditor on the Audit Plan
- you need to re-login after a fresh assignment

### 4.4 Step-by-step: complete engagement planning

1. In `Create Engagement Plan`, review the prefilled data.
2. Update:
   - Title
   - Objective
   - Scope
   - Scope Exclusions
   - Audit Period From / To
   - Kickoff Date
   - Planned Start / End
   - Reviewer
   - Auditee SPOC
   - Planned Hours
   - Approved Hours
3. Click `Save`.
4. Open the created engagement record.
5. Review the tabs:
   - `Overview`
   - `Kickoff Checklist`
   - `Resource Budget`
   - `Documents`
6. Upload the Engagement Letter in `Documents`.

Note:

- the Engagement Letter is recommended workflow guidance
- it does not hard-block later audit work yet

### 4.5 Step-by-step: execute the audit

1. Open `Manage Audits`.
2. Click `View` on the audit.
3. Use the audit detail page to work through:
   - audit profile
   - members
   - activities
   - observations
   - action plans

### 4.6 Step-by-step: activities

1. Open `My Activities` for personal tasks.
2. Or open the audit detail page to manage all audit activities.
3. Create or update activities with:
   - title
   - objective
   - due date
   - assignee
   - status
   - remarks
4. Move activities through:
   - Yet to Start
   - Work in Progress
   - Completed
   - Not Applicable

### 4.7 Step-by-step: workpapers and evidence

1. Open `Workpapers`.
2. Create a workpaper for the audit or related activity.
3. Upload versions as fieldwork progresses.
4. Submit the workpaper for review.
5. Review and sign-off flow moves through:
   - Draft
   - Submitted for Review
   - Reviewed
   - Approved
   - Locked

For evidence:

1. Open `Evidence Register`
2. Register evidence item
3. Link it to the appropriate module
   - workpaper
   - observation
   - other supported record

### 4.8 Step-by-step: raise an observation

1. Open the audit detail page or `Observations`.
2. Create a new observation.
3. Complete the required fields:
   - heading
   - observation text
   - risk type
   - observation grading
   - root cause if available
   - assigned auditee
4. Save as draft if still being refined.
5. Issue the observation to the auditee.

Expected result:

- observation status moves from `Draft` to `Issued`
- the auditee can now see it in their portal

### 4.9 Step-by-step: review auditee response

1. Open `Observations`.
2. Review the auditee remark once the item moves to `Responded`.
3. Decide whether to:
   - accept it
   - drop it
   - convert it to an action plan

### 4.10 Step-by-step: action plans

1. Convert an accepted observation into an Action Plan.
2. Review the generated record in `Action Plans`.
3. Track status, timeline, and auditee implementation remarks.
4. Reopen if necessary.

## 5. Auditee Manual

### 5.1 Main responsibility

The auditee responds to findings and updates remediation progress. This role is responsible for:

- reviewing issued observations
- submitting remarks / response
- updating action-plan implementation remarks

### 5.2 What the auditee can expect to see

The auditee does not have broad audit-management controls.

The auditee mainly works in:

- `Observations`
- `Action Plans`
- `Reports` if permitted

### 5.3 Step-by-step: respond to an observation

1. Log in as the assigned auditee.
2. Open [Observations](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/apps/web/app/(app)/observations/page.tsx).
3. Open the issued observation assigned to you.
4. Review the finding details.
5. Enter your remark / response.
6. Submit the response.

Expected result:

- the observation moves into the response stage
- the assigned auditor can now review your response

### 5.4 Step-by-step: update action-plan remarks

1. Open [Action Plans](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/apps/web/app/(app)/action-plans/page.tsx).
2. Open the action plan assigned to you.
3. Update only your allowed implementation remarks.
4. Save the remarks.

Important:

- auditees do not get delete rights
- auditees do not get broad edit rights on controlled workflow fields
- auditee contribution is intentionally restricted to response / remarks behavior

## 6. End-to-End Example

This is the simplest working example for business users:

1. Head Auditor creates an Audit Plan
2. Head Auditor assigns `Auditor User 1` as Lead Auditor
3. Head Auditor submits and approves the Audit Plan
4. Head Auditor clicks `Initiate Audit`
5. `Auditor User 1` logs in
6. `Auditor User 1` opens `Manage Audits`
7. The initiated audit is visible there
8. `Auditor User 1` clicks `Start Engagement`
9. Engagement Planning opens with audit defaults prefilled
10. Auditor saves the engagement plan
11. Auditor performs activities, workpapers, and evidence collection
12. Auditor raises an observation for the auditee
13. Auditee logs in and responds to the observation
14. Auditor reviews the response and converts it into an Action Plan if required
15. Auditee updates implementation remarks
16. Auditor tracks closure

## 7. Common Troubleshooting

### 7.1 I approved the Audit Plan but the auditor cannot see the audit

Check this sequence:

1. Was the plan only approved, or was it also initiated?
2. Was a Lead Auditor assigned on the Audit Plan before initiation?
3. Did the auditor log out and back in after the change?

### 7.2 The `Select Audit` dropdown in Engagement Planning is empty

Possible reasons:

- the audit is not initiated yet
- the logged-in auditor is not the assigned Lead Auditor
- the browser session is stale after a recent assignment

### 7.3 The auditee cannot edit everything

That is expected behavior.

The auditee is intentionally restricted to:

- observation response / remark
- action plan implementation remarks

### 7.4 I cannot see a module in the sidebar

The tool uses permission-based navigation. Missing menu items usually mean:

- your role does not have access
- your session is stale after a permission change

## 8. Good Operating Practice

For Head Auditors:

- always assign the Lead Auditor before initiation
- use clear reviewer and auditee SPOC assignment where relevant

For Auditors:

- start engagement from `Manage Audits`
- keep workpapers and evidence linked early
- issue observations only when the draft is ready

For Auditees:

- respond promptly to issued observations
- keep implementation remarks factual and current

## 9. Recommended Companion Documents

For technical and control reference, also use:

- [README.md](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/README.md)
- [RBAC_MATRIX.md](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/RBAC_MATRIX.md)
- [WORKFLOW_NOTES.md](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/WORKFLOW_NOTES.md)
- [API_DOCUMENTATION.md](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/API_DOCUMENTATION.md)
