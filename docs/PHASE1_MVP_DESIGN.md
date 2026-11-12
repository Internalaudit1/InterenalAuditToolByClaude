# Internal Audit Management Tool — Phase-1 MVP Design

*Prepared as: Product Architect + Internal Audit practitioner. Audience: IA Head (product owner) and the development team.*
*Status: Approved design · July 2026 · Grounded in the existing codebase (branch `codex/stabilization-checkpoint-20260604`)*

---

## 1. Phase-1 Product Vision

**One line:** *A guided digital audit file — not an enterprise system.*

The tool should feel like the audit file your team already maintains manually: a front index, a plan, an engagement letter, a program, working notes, observations, and a report — in that order. Every audit is one workspace with seven steps shown left-to-right. An auditor should never ask *"where do I go next?"* — the file tells them.

**Phase-1 promise to the IA team:**
- Everything you do today in Excel/Word, you can do here — same vocabulary, same order.
- Nothing is more than 2 clicks from the audit workspace.
- The tool never blocks you: letters open in Outlook, reports export to Word, plans import from Excel.
- What the Audit Committee approved stays locked; who does what stays visible.

**What Phase 1 deliberately does NOT do:** workpaper versioning, evidence registers, risk-scoring engines, automated email, analytics. Those exist in the codebase already (or are planned) and return in Phase 2 once the team is comfortable.

---

## 2. Module Structure (clean, 5 menus + Admin)

```
📊 Dashboard                        (role-based "my work" view)
🗂️ Audit Universe                   (universe register + risk mapping)
📅 Audit Plan
     ├─ Annual Plan                 (list + Excel import)
     ├─ Plan Approvals              (Head only)
     └─ Audit Assignment            (Head only)
📁 Manage Audit                     (list of audits → each opens the 7-step file)
     Step A  Engagement Letter / Announcement
     Step B  Audit Program
     Step C  Fieldwork Execution        (same grid as B)
     Step D  Observations
     Step E  Draft Report
     Step F  Management Action Plans
     Step G  Final Report & Closure
✅ Action Plans                     (cross-audit tracker: open / overdue / closed)
⚙️ Admin                            (Super Admin only: users, roles, masters, logs)
```

Compare with today: 12+ top-level menus (Workpapers, Evidence, Engagement Plans, Knowledge Library, My Activities, Reports, Masters with 20 children…). Phase 1 shows **5**. Everything hidden remains in the database and code — re-enabled per module in Phase 2 by restoring a menu entry and a permission.

---

## 3. User Journeys

### 3.1 Audit Head — "from universe to assignment" (once a year + quarterly touch-ups)

1. Open **Audit Universe** → import or type the list of auditable areas (department, process, location, owner, risk rating, frequency, last audit date).
2. The register flags what is **Due** (last audit date + frequency).
3. Open **Audit Plan → Annual Plan** → click **Build from Universe** → tick the areas to audit this year → each becomes a plan line with an auto number (AUD-2026-0001…).
4. Submit the plan → **Approve** it (plan becomes locked; only remarks editable — your Audit Committee copy).
5. Open **Audit Assignment** → for each approved plan line: pick Lead Auditor, up to two Junior Auditors, a Mentor (reviewer), period and dates → **Approve allocation** → **Initiate audit**.
6. The audit now appears in **Manage Audit** for the assigned team, and on their dashboards.

### 3.2 Auditor — "one audit, seven steps" (per audit)

1. Dashboard shows **My Audits** → open "Procurement Audit FY27" → the 7-step file opens at Step A.
2. **Step A:** fill the engagement letter form → Preview → **Open in Outlook** → send manually → upload the sent copy → mark step complete.
3. **Step B:** build the audit program — one row per test: process, risk, control, test objective, test step, sample. (Or copy from a previous audit / import from Excel.)
4. **Step C:** during fieldwork, update each row: status (Not Started → In Progress → Completed / Exception Noted / N.A.), remarks, evidence attachment, test date.
5. **Step D:** for every "Exception Noted" row, click **Raise Observation** → the form pre-fills the linked test step → complete title, background, criteria, condition, cause, impact, recommendation, rating → save. **Issue** it to the auditee when ready.
6. Auditee responds in the tool; auditor **Accepts** (or returns) the observation.
7. **Step E:** click **Generate Draft Report** → Word file with all accepted observations → review offline, upload the final version.
8. **Step F:** accepted observations are converted to **Action Plans** with owner + target date; track responses.
9. **Step G:** run the closure checklist (report final? all observations concluded? APs logged?) → **Close Audit**.

### 3.3 Auditee / Management — "respond and act" (only what concerns them)

1. Email/notification: *"Observation OBS-2026-0005 has been issued to you."*
2. Log in → see **only** their observations and action plans (nothing else in the menu).
3. Open the observation → read → type management response → attach proof → **Submit**.
4. When it becomes an action plan: update status, add implementation remarks, attach evidence, watch the target date.
5. Management role: read-only overview of audits + action plan status.

---

## 4. Dashboard Design (role-based, one screen, no configuration)

| Zone | Audit Head | Auditor | Auditee |
|---|---|---|---|
| Top tiles (4) | Audits: Planned / In Progress / Completed / Overdue | My audits / My open test steps / My draft observations / My pending steps | Observations awaiting my response / My open APs / Overdue APs / Closed this quarter |
| Middle | Plan coverage bar: approved vs assigned vs initiated vs closed | **My Audits** table with step-progress bar per audit (A→G) | My observations list with status chips |
| Bottom | Overdue action plans (top 10, by days overdue) | My pending actions ("3 test steps overdue", "1 observation awaiting issue") | My action plans with target dates |

Implementation note: reuses the existing `stat-grid` + chart components and `/dashboard/summary` service — this is a filter change, not a rebuild.

---

## 5. Data Flow — Universe to Final Report

```
AUDIT UNIVERSE ──(select areas)──► ANNUAL AUDIT PLAN ──(approve = lock)──► AUDIT ASSIGNMENT
   │ risk mapping                        AUD-YYYY-####                        ALC-YYYY-####
   │ (risks per area)                                                              │ initiate
   ▼                                                                               ▼
                                                                              AUDIT (live file)
                                                                                   │
        ┌────────────── 7-step audit file ─────────────────────────────────────────┤
        ▼                ▼                    ▼                   ▼                ▼
  A ENGAGEMENT      B/C PROGRAM +        D OBSERVATIONS      E DRAFT          G CLOSURE
    LETTER            FIELDWORK            OBS-YYYY-####       REPORT           checklist
    (Outlook)         (test steps)             │               (Word/PDF)
                          │ exception          ▼
                          └──────────► F ACTION PLANS  ACT-YYYY-####
                                         (auditee responds, IA tracks)
```

All reference numbers (AUD, ALC, OBS, ACT) are **already generated automatically** by the existing backend — concurrency-safe, immutable. New in Phase 1: program steps and letters hang off the audit; the report is generated from observations.

---

## 6. Menu Structure with Role Visibility

| Menu | Head Auditor | Auditor / Junior | Auditee | Management | Super Admin |
|---|---|---|---|---|---|
| Dashboard | ✔ | ✔ | ✔ (their view) | ✔ (read) | ✔ |
| Audit Universe | ✔ edit | view | — | view | ✔ |
| Audit Plan → Annual Plan / Import | ✔ | view | — | view | ✔ |
| Audit Plan → Approvals | ✔ | — | — | — | ✔ |
| Audit Plan → Assignment | ✔ | view own | — | view | ✔ |
| Manage Audit (7 steps) | ✔ all audits | ✔ assigned only | steps D & F only, own items | view | ✔ |
| Action Plans | ✔ | ✔ assigned | ✔ own only | view | ✔ |
| Admin | — | — | — | — | ✔ |

Developer note: this is mostly **deletion** in `apps/web/lib/navigation.ts` (remove Workpapers, Evidence, Engagement Plans, Knowledge Library, My Activities, Reports*, most Masters children) and trimming role permission sets in `apps/api/app/core/permissions.py`. (*Reports as a separate menu disappears — the draft report lives inside the audit file at Step E.)

---

## 7. Database Entities (plain language)

### Reused unchanged (already built and tested)
| Table | Holds | Phase-1 role |
|---|---|---|
| `audit_plans` | Annual plan lines, AUD number, approval lock | Annual Plan |
| `audit_allocations` | Assignment: lead, juniors, mentor, dates, ALC number | Audit Assignment |
| `audits` + `audit_memberships` | The live audit + who is on it | Manage Audit shell |
| `observations` | Observation with lifecycle Draft→Issued→Responded→Accepted→Converted | Step D |
| `action_plans` + `action_plan_revisions` | MAP with dual auditor/auditee status + history | Step F / Action Plans |
| `attachments` | Every uploaded file, with owner linkage | Evidence on steps A–F |
| `users`, `roles`, `permissions` | Access control | throughout |
| `activity_logs`, `notifications` | Trail + in-app alerts | throughout |
| `companies`, `locations`, `processes` | Master data | lookups |

### New tables (4 small ones)
| Table | Fields (simple terms) |
|---|---|
| `audit_universe_items` | entity/department, process, sub-process, location (FK), audit owner (user FK), risk category, risk rating (H/M/L), last audit date, audit frequency (Annual / 2-Yearly / Quarterly), status (Active/Inactive), notes. Computed: **next due** = last audit + frequency |
| `universe_risks` | universe_item (FK), risk description, risk category, inherent rating, existing controls (text), control owner, residual rating |
| `audit_program_steps` | audit (FK), sequence no., process, sub-process, narrative, risk, control, control design (Adequate/Inadequate), test objective, test step, sample selected, workpaper reference (free text), remarks, testing status (Not Started / In Progress / Completed / Exception Noted / N.A.), tested on (date), tested by (user FK), evidence attachment (FK), linked observation (FK, set when exception is raised) |
| `engagement_letters` | audit (FK), auditee department, scope text, audit period, start/end dates, information required (text), introduction text, generated letter body, sent date, sent copy attachment (FK), status (Draft / Sent / Filed) |

### Small additions to existing tables (no columns changed or removed)
- `audit_plans.universe_item_id` (nullable FK) — links a plan line back to the universe area it came from.
- `observations.criteria` and `observations.cause_description` (nullable text) — completes the 5-C observation format (Condition/Criteria/Cause/Consequence/Corrective action). Background, condition (observation_text), impact (risk_implication), recommendation, root-cause lookup already exist.
- `audits.closure_status`, `audits.closed_at`, `audits.final_report_attachment_id` (nullable) — Step G.

---

## 8. Wireframes (text)

### 8.1 Audit Universe register
```
AUDIT UNIVERSE                                        [+ Add Area] [Import Excel]
Filters: [Entity ▾] [Location ▾] [Risk ▾] [Due status ▾]        Search: [____]
┌────┬──────────────┬─────────────┬──────────┬──────┬────────────┬───────────┬────────┐
│ #  │ Entity/Dept  │ Process     │ Location │ Risk │ Last Audit │ Frequency │ Due?   │
├────┼──────────────┼─────────────┼──────────┼──────┼────────────┼───────────┼────────┤
│ 1  │ Procurement  │ P2P         │ Noida    │ High │ Mar 2025   │ Annual    │ 🔴 DUE │
│ 2  │ Finance      │ R2R         │ Chennai  │ Med  │ Aug 2025   │ Annual    │ ⚪ Aug │
└────┴──────────────┴─────────────┴──────────┴──────┴────────────┴───────────┴────────┘
Row click → side panel: details + "Risks for this area" mini-grid (add/edit risk rows)
```

### 8.2 Plan builder (from Universe)
```
BUILD ANNUAL PLAN — FY 2026-27                          [Import Excel instead]
Showing universe areas · sorted DUE first
[✔] Procurement / P2P / Noida        High   DUE     → planned Q1  [dates]
[✔] IT General Controls / Gurgaon    High   DUE     → planned Q2  [dates]
[ ] Finance / R2R / Chennai          Med    Aug-26
                              [Create 2 Plan Lines →]   (numbers auto: AUD-2026-…)
```

### 8.3 Audit Assignment board (existing screen, relabeled)
```
AUDIT ASSIGNMENT
┌ AUD-2026-0001 Procurement ─ Approved plan ─────────────────────────────┐
│ Lead: [Priya ▾]  Junior 1: [Rahul ▾]  Junior 2: [– ▾]  Mentor: [Vikram ▾]│
│ Period: [Q1 ▾]  Start: [05-Apr]  Target end: [30-Apr]                   │
│ [Save Draft]  [Approve Allocation]  → then [Initiate Audit]             │
└──────────────────────────────────────────────────────────────────────────┘
```

### 8.4 Manage Audit — the 7-step file (the heart of the tool)
```
AUD-2026-0001 · PROCUREMENT AUDIT · Q1 FY27 · Lead: Priya
● A Letter ─ ● B Program ─ ◐ C Fieldwork ─ ○ D Observations ─ ○ E Report ─ ○ F APs ─ ○ G Close
                                (click any step to open; ●done ◐in-progress ○pending)
┌─ Step C: Fieldwork ──────────────────────────────────────────────────────┐
│  12 test steps · 7 completed · 2 exceptions · 3 in progress              │
│  [open program grid]                                                     │
└──────────────────────────────────────────────────────────────────────────┘
Right rail: audit facts (dates, team, status) + recent activity
```

### 8.5 Engagement Letter (Step A)
```
ENGAGEMENT LETTER — AUD-2026-0001
Auditee dept: [Procurement]   SPOC: [Mr. Sharma ▾]
Scope: [textarea]             Period: [Apr'25–Mar'26]
Dates: [05-Apr] → [30-Apr]    Information required: [textarea, one per line]
Intro message: [textarea, pre-filled standard courtesy paragraph]
[Preview Letter]  →  formatted letter view
[📧 Open in Outlook]   ← opens draft mail (To: SPOC, Subject, Body = letter)
After sending: [Upload sent copy ⬆]  →  status: SENT ✔ filed on 05-Apr
```

### 8.6 Audit Program / Fieldwork grid (Steps B+C — one grid)
```
AUDIT PROGRAM — 12 steps                    [+ Add Step] [Copy from audit ▾] [Import]
┌───┬─────────┬────────────────┬──────────────┬────────────────┬─────────┬───────────────┬──────────┐
│ # │ Process │ Risk           │ Control      │ Test step      │ Sample  │ Status        │ Evidence │
├───┼─────────┼────────────────┼──────────────┼────────────────┼─────────┼───────────────┼──────────┤
│ 1 │ P2P     │ Unauthorized PO│ PO approval  │ Check 25 POs   │ 25 POs  │ ✅ Completed  │ 📎 2     │
│ 2 │ P2P     │ Split PO       │ Threshold ctl│ Scan FY POs    │ Full pop│ 🔴 Exception  │ 📎 1     │
│   │         │                │              │                │         │ [Raise Obs →] │          │
└───┴─────────┴────────────────┴──────────────┴────────────────┴─────────┴───────────────┴──────────┘
Row click → drawer: narrative, control design, objective, remarks, tested by/on, attach evidence
```

### 8.7 Observation form (Step D)
```
OBSERVATION — OBS-2026-0005                      linked: program step #2
Title [____________]                              Rating [High ▾]
Background / Criteria (policy) / Condition (issue) / Cause / Risk & Impact /
Recommendation  — six textareas in the 5-C order auditors know
Auditee: [Mr. Sharma ▾]   Evidence: [📎 attach]
[Save Draft]  [Issue to Auditee]        status chip: DRAFT
--- after response ---
Management response (read-only, from auditee) → [Accept] [Return] → [Convert to Action Plan]
```

### 8.8 Closure checklist (Step G)
```
AUDIT CLOSURE — AUD-2026-0001
[✔] Final report uploaded            (FR_Procurement_FY27.docx, 12-May)
[✔] All observations concluded       (5 accepted → converted, 1 dropped)
[✔] Action plans created             (5 APs, owners + target dates set)
[ ] Auditee sign-off received        (optional attachment)
Pending: none blocking                        [Close Audit]
Closed audits become read-only; APs continue tracking in the Action Plans menu.
```

---

## 9. Phase-1 vs Phase-2

| Capability | Phase 1 | Phase 2 | Note |
|---|---|---|---|
| Universe register + risk mapping | ✔ simple | scoring engine, heatmaps | |
| Annual plan + approval lock + import | ✔ (built) | plan amendments workflow | amendment path is a known gap |
| Assignment (lead/juniors/mentor) | ✔ (built) | capacity/workload view | |
| Engagement letter + Outlook draft | ✔ | automated email (SMTP), templates library | `NotificationOutbox` table already scaffolded |
| Program + fieldwork grid | ✔ | control library / RCM, sampling tools | |
| Observations full lifecycle | ✔ (built) | AI-drafting, recurring-issue tracker | |
| Draft report (Word/PDF) | ✔ template-fill | report designer, exec dashboards | |
| Action plans + tracking | ✔ (built) | follow-up audit automation | |
| Closure checklist | ✔ | QA review workflow | |
| Workpapers (versioned) & Evidence register | hidden | re-enable (already built) | zero rework |
| Rich engagement planning (kickoff, budgets) | hidden | re-enable (already built) | |
| Knowledge library, analytics, compliance mapping, policy library | hidden/absent | build/enable | |

---

## 10. Implementation Roadmap (4 sprints ≈ 8 weeks)

| Sprint | Scope | Why this order |
|---|---|---|
| 1 (wk 1–2) | Navigation slim-down + permission trim; Universe register (table, CRUD, Excel import, due-flag); universe→plan builder | Team sees the simpler tool immediately; Head can start the FY plan |
| 2 (wk 3–4) | Manage Audit 7-step shell; Engagement letter (form, preview, mailto, filed copy); program/fieldwork grid | The core daily-work surface |
| 3 (wk 5–6) | Raise-observation-from-step link; criteria/cause fields; draft report generator (docx); closure checklist + fields | Completes the file A→G |
| 4 (wk 7–8) | Role-based dashboards; pilot **one real audit** end-to-end with the IA team; fix friction; training pack | Adoption is the deliverable |

Honest sizing: ~60% of Phase 1 is **already built and tested** (plan, assignment, observations, APs, dashboard, auth, files). New build = 4 small tables + 4 screens + 1 document generator + navigation cuts.

---

## 11. Reducing Complexity & Driving Adoption

1. **Pilot one audit, not a rollout.** Pick a friendly auditee; run one audit fully in the tool; make that team the champions.
2. **Excel in, Word out.** Universe and plans import from the sheets they already keep; reports export to Word they can polish. The tool never traps their data.
3. **Train with their vocabulary.** The 7 steps *are* their manual file index — teach it as "your audit file, now digital", never "the system workflow".
4. **Minimal mandatory fields.** Only what a number or a lifecycle needs (e.g., observation title + rating). Everything else can be completed later.
5. **Manual escape hatches by design.** Outlook draft instead of SMTP; uploaded final report instead of forced in-tool authoring; free-text workpaper references instead of a repository.
6. **One screen, one purpose.** No tabs-inside-tabs; the step bar is the only navigation inside an audit.
7. **Show progress, not controls.** Dashboards answer "what's pending on me?" — the fastest habit-forming loop.

---

## 12. Missing but Compulsory for Phase 1 (added to design)

- **Audit closure step** — without an explicit close, audits stay "in progress" forever and the plan never shows done.
- **Observation `criteria` + `cause` fields** — the 5-C format is an IA-standard expectation; the model lacks two of the five.
- **Filed copy of the sent engagement letter** — the audit record must show what was announced and when.
- **Draft report generation from observations** — the single biggest time-saver vs manual work; without it the tool feels like extra data entry.
- **"Due" computation on the universe** — the one piece of intelligence that makes the universe worth maintaining.

## 13. Remove / Hide from Phase 1 (currently exposed)

| Item | Action |
|---|---|
| Workpapers (versioning, reviews, sign-off) | Hide menu + permissions; program grid's free-text "workpaper ref" replaces it |
| Evidence Register (+ confidentiality levels, cross-links) | Hide; step-level attachments suffice |
| Engagement Plans module (kickoff checklist, resource budgeting, hours) | Hide; Step A letter + assignment dates cover Phase-1 need |
| Knowledge Library | Hide |
| My Activities queue | Hide; dashboard "my pending steps" replaces it |
| Reports menu (generic inventory export) | Fold into dashboard export button; report generation moves inside the audit (Step E) |
| Masters menu (20 children) | Admin-only; auditors never see it |
| Management review notes on APs | Hide from Phase 1 UI (backend stays) |
| Data Explorer | Admin-only |

## 14. Final MVP Spec for Developers (hand-off summary)

**Principle: reuse first.** No existing table is modified destructively; no existing module is deleted.

**Backend — new:**
- Models: `AuditUniverseItem`, `UniverseRisk`, `AuditProgramStep`, `EngagementLetter` (+ 3 nullable columns: `audit_plans.universe_item_id`; `observations.criteria`, `observations.cause_description`; `audits.closure_status/closed_at/final_report_attachment_id`). One Alembic migration, additive only.
- Routes/services: `/universe` CRUD + Excel import (copy the `audit_plan_import.py` validate→commit pattern); `/audits/{id}/program-steps` CRUD + status update + raise-observation; `/audits/{id}/engagement-letter` (create, preview, mark-sent, attach copy — mailto assembled client-side); `/audits/{id}/draft-report` (python-docx template fill → .docx download; reuse `reporting.py` streaming pattern); `/audits/{id}/close` (checklist validation).
- Permissions: new `universe:view/manage`, `program:view/manage`, reuse existing observation/AP/plan permissions; trim Phase-2 permissions from auditor/junior/auditee role sets in `core/permissions.py`.

**Frontend — new/changed:**
- `lib/navigation.ts` → the 5-menu tree (section 6).
- New pages: `/universe`, `/audits/[id]` rebuilt as the 7-step file shell (steps as components), letter form, program grid, closure checklist.
- Reused as-is: assignment (`/audit-allocations`, relabeled), plan import, observations lifecycle UI, action plans, dashboard components.

**Reuse map (existing, keep):** `models/audit.py` (AuditPlan/AuditAllocation/Observation), `models/action_plan.py`, `services/audit_allocation.py`, `services/audit_plan_import.py`, `services/file_storage.py`, `routes/planning.py`, reference-number generation (`models/reference_counter.py` + PG triggers) — all untouched.

**Acceptance test (the pilot audit):** Universe entry → plan line → approve → assign → initiate → letter sent via Outlook + filed → 5+ program steps → 1 exception → observation issued → auditee responds in portal → accepted → converted to AP → draft report generated in Word → closure checklist → audit closed → AP still tracking. If one auditor completes this unaided after a 30-minute demo, Phase 1 ships.
