"use client";

import { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { use, useEffect, useState } from "react";

import { AsyncLookupField } from "@/components/forms/async-lookup";
import { RichTextEditor } from "@/components/forms/rich-text-editor";
import { PageShell } from "@/components/layout/page-shell";
import { DataTable } from "@/components/table/data-table";
import { apiFetch } from "@/lib/api";

const actionColumns: ColumnDef<Record<string, unknown>>[] = [
  { accessorKey: "action_plan_id", header: "Action Plan" },
  { accessorKey: "observation_id", header: "Observation ID" },
  { accessorKey: "observation_heading", header: "Observation" },
  { accessorKey: "auditor_status", header: "Auditor Status" },
  { accessorKey: "auditee_status", header: "Auditee Status" }
];

const memberColumns: ColumnDef<Record<string, unknown>>[] = [
  { accessorKey: "user_name", header: "User" },
  { accessorKey: "role_on_audit", header: "Role on Audit" }
];

const activityColumns: ColumnDef<Record<string, unknown>>[] = [
  { accessorKey: "title", header: "Activity" },
  { accessorKey: "assigned_to_name", header: "Assigned To" },
  { accessorKey: "due_date", header: "Due Date" },
  { accessorKey: "status", header: "Status" },
  { accessorKey: "remarks", header: "Remarks" }
];

const observationColumns: ColumnDef<Record<string, unknown>>[] = [
  { accessorKey: "observation_number", header: "Observation" },
  { accessorKey: "heading", header: "Heading" },
  { accessorKey: "status", header: "Status" },
  { accessorKey: "auditee_name", header: "Auditee" },
  { accessorKey: "auditee_remark", header: "Auditee Remark" }
];

export default function AuditDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [audit, setAudit] = useState<any>(null);
  const [actions, setActions] = useState<Record<string, unknown>[]>([]);
  const [members, setMembers] = useState<Record<string, unknown>[]>([]);
  const [activities, setActivities] = useState<Record<string, unknown>[]>([]);
  const [observations, setObservations] = useState<Record<string, unknown>[]>([]);
  const [completion, setCompletion] = useState<{ completed: number; total: number; percentage: number } | null>(null);
  const [activityForm, setActivityForm] = useState({ title: "", assigned_to_user_id: "", assigned_to_user_label: "", due_date: "" });
  const [observationForm, setObservationForm] = useState({
    heading: "",
    observation_text: "",
    observation_grading_id: "",
    risk_type_id: "",
    auditee_id: "",
    auditee_label: ""
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function load() {
    const [auditData, actionData, memberData, activityData, observationData, completionData] = await Promise.all([
      apiFetch<any>(`/audits/${id}`),
      apiFetch<{ items: Record<string, unknown>[] }>(`/action-plans?audit_id=${id}&page_size=100`),
      apiFetch<Record<string, unknown>[]>(`/audits/${id}/members`),
      apiFetch<{ items: Record<string, unknown>[] }>(`/audits/${id}/activities?page_size=100`),
      apiFetch<{ items: Record<string, unknown>[] }>(`/audits/${id}/observations?page_size=100`),
      apiFetch<{ completed: number; total: number; percentage: number }>(`/audits/${id}/completion`)
    ]);
    setAudit(auditData);
    setActions(actionData.items);
    setMembers(memberData);
    setActivities(activityData.items);
    setObservations(observationData.items);
    setCompletion(completionData);
  }

  useEffect(() => {
    load().catch((err) => setError((err as Error).message));
  }, [id]);

  if (!audit) return null;

  return (
    <PageShell title={audit.audit_name} eyebrow={audit.audit_number} description="Manage audit execution details, lifecycle history, and linked action plans from one place.">
      <section className="panel p-6">
        <div className="grid gap-4 md:grid-cols-3">
          <div><p className="chip">Status</p><p className="mt-3 text-lg font-semibold">{audit.status}</p></div>
          <div><p className="chip">Period</p><p className="mt-3 text-lg font-semibold">{audit.period_type ?? "Period"} / {audit.period_value ?? audit.quarter}</p></div>
          <div><p className="chip">Criticality</p><p className="mt-3 text-lg font-semibold">{audit.criticality}</p></div>
        </div>
        <div className="mt-6 rounded-2xl border border-sand bg-cream p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="font-semibold">Completion</p>
            <p className="text-sm text-slate">{completion?.completed ?? 0} of {completion?.total ?? 0} activities completed</p>
          </div>
          <div className="mt-3 h-3 overflow-hidden rounded-full bg-white">
            <div className="h-full rounded-full bg-ink" style={{ width: `${completion?.percentage ?? 0}%` }} />
          </div>
        </div>
        <div className="mt-6">
          <h2 className="font-serif text-2xl">Audit History Timeline</h2>
          <div className="mt-4 space-y-3">
            {(audit.history_timeline ?? []).map((entry: { status: string; date: string; note?: string }) => (
              <div key={`${entry.status}-${entry.date}`} className="rounded-2xl border border-sand bg-cream p-4">
                <p className="font-semibold">{entry.status}</p>
                <p className="text-sm text-slate">{entry.date}</p>
                {entry.note ? <p className="mt-2 text-sm text-slate">{entry.note}</p> : null}
              </div>
            ))}
          </div>
        </div>
      </section>
      {success ? <div className="rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{success}</div> : null}
      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      <section className="panel p-6">
        <div className="flex flex-wrap gap-3">
          <Link href={`/workpapers?audit_id=${id}`} className="button-secondary px-4 py-2">
            Workpapers
          </Link>
          <Link href={`/evidence?audit_id=${id}`} className="button-secondary px-4 py-2">
            Evidence Register
          </Link>
        </div>
      </section>
      <section>
        <h2 className="mb-4 font-serif text-2xl">Audit Members</h2>
        <DataTable columns={memberColumns} data={members} />
      </section>
      <section className="panel p-6">
        <h2 className="font-serif text-2xl">Activities</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <input className="field" placeholder="Activity title" value={activityForm.title} onChange={(event) => setActivityForm((prev) => ({ ...prev, title: event.target.value }))} />
          <AsyncLookupField
            value={activityForm.assigned_to_user_id}
            selectedLabel={activityForm.assigned_to_user_label}
            endpoint="/admin/users"
            queryParam="q"
            placeholder="Search Assigned User"
            staticParams={{ active_only: true, roles: "super_admin,head_auditor,auditor,junior_auditor,management" }}
            mapOption={(row) => ({
              value: row.id as number,
              label: String(row.full_name ?? row.username ?? row.id),
              description: [row.designation_title, row.company_name, row.location_label].filter(Boolean).join(" - ")
            })}
            onSelect={(option) => setActivityForm((prev) => ({
              ...prev,
              assigned_to_user_id: option ? String(option.value) : "",
              assigned_to_user_label: option?.label ?? ""
            }))}
          />
          <input className="field" type="date" value={activityForm.due_date} onChange={(event) => setActivityForm((prev) => ({ ...prev, due_date: event.target.value }))} />
          <button
            className="button-primary"
            onClick={async () => {
              try {
                await apiFetch(`/audits/${id}/activities`, {
                  method: "POST",
                  body: JSON.stringify({
                    title: activityForm.title,
                    assigned_to_user_id: activityForm.assigned_to_user_id ? Number(activityForm.assigned_to_user_id) : null,
                    due_date: activityForm.due_date || null
                  })
                });
                setActivityForm({ title: "", assigned_to_user_id: "", assigned_to_user_label: "", due_date: "" });
                setSuccess("Activity created.");
                setError("");
                await load();
              } catch (err) {
                setSuccess("");
                setError((err as Error).message);
              }
            }}
          >
            Add Activity
          </button>
        </div>
        <div className="mt-5">
          <DataTable columns={activityColumns} data={activities} />
        </div>
      </section>
      <section className="panel p-6">
        <h2 className="font-serif text-2xl">Observations</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <input className="field" placeholder="Observation heading" value={observationForm.heading} onChange={(event) => setObservationForm((prev) => ({ ...prev, heading: event.target.value }))} />
          <input className="field" placeholder="Grading ID" value={observationForm.observation_grading_id} onChange={(event) => setObservationForm((prev) => ({ ...prev, observation_grading_id: event.target.value }))} />
          <input className="field" placeholder="Risk Type ID" value={observationForm.risk_type_id} onChange={(event) => setObservationForm((prev) => ({ ...prev, risk_type_id: event.target.value }))} />
          <AsyncLookupField
            value={observationForm.auditee_id}
            selectedLabel={observationForm.auditee_label}
            endpoint="/master/auditees"
            queryParam="search"
            placeholder="Search Auditee"
            staticParams={{ is_active: true }}
            mapOption={(row) => ({
              value: row.id as number,
              label: String(row.full_name ?? row.auditee_code ?? row.id),
              description: [row.auditee_code, row.designation, row.department].filter(Boolean).join(" - ")
            })}
            onSelect={(option) => setObservationForm((prev) => ({
              ...prev,
              auditee_id: option ? String(option.value) : "",
              auditee_label: option?.label ?? ""
            }))}
          />
          <div className="md:col-span-2">
            <RichTextEditor
              value={observationForm.observation_text}
              onChange={(nextValue) => setObservationForm((prev) => ({ ...prev, observation_text: nextValue }))}
              placeholder="Observation text"
              minHeightClass="min-h-24"
            />
          </div>
          <button
            className="button-primary"
            onClick={async () => {
              try {
                await apiFetch(`/audits/${id}/observations`, {
                  method: "POST",
                  body: JSON.stringify({
                    heading: observationForm.heading,
                    observation_text: observationForm.observation_text,
                    observation_grading_id: Number(observationForm.observation_grading_id),
                    risk_type_id: Number(observationForm.risk_type_id),
                    auditee_id: observationForm.auditee_id ? Number(observationForm.auditee_id) : null
                  })
                });
                setObservationForm({ heading: "", observation_text: "", observation_grading_id: "", risk_type_id: "", auditee_id: "", auditee_label: "" });
                setSuccess("Observation drafted.");
                setError("");
                await load();
              } catch (err) {
                setSuccess("");
                setError((err as Error).message);
              }
            }}
          >
            Draft Observation
          </button>
        </div>
        <div className="mt-5">
          <DataTable
            columns={observationColumns}
            data={observations}
            renderRowActions={(row) => (
              <div className="flex flex-wrap gap-2">
                {row.status === "Draft" ? (
                  <button className="button-secondary px-4 py-2" onClick={async () => {
                    try {
                      await apiFetch(`/observations/${row.id}/issue`, { method: "POST", body: JSON.stringify({}) });
                      setSuccess("Observation issued.");
                      setError("");
                      await load();
                    } catch (err) {
                      setSuccess("");
                      setError((err as Error).message);
                    }
                  }}>Issue</button>
                ) : null}
                {row.status === "Responded" || row.status === "Issued" ? (
                  <button className="button-secondary px-4 py-2" onClick={async () => {
                    try {
                      await apiFetch(`/observations/${row.id}/accept`, { method: "POST", body: JSON.stringify({}) });
                      setSuccess("Observation accepted.");
                      setError("");
                      await load();
                    } catch (err) {
                      setSuccess("");
                      setError((err as Error).message);
                    }
                  }}>Accept</button>
                ) : null}
                {row.status === "Accepted" ? (
                  <button className="button-secondary px-4 py-2" onClick={async () => {
                    const agreed_timeline = window.prompt("Agreed timeline (YYYY-MM-DD)");
                    if (!agreed_timeline) return;
                    try {
                      await apiFetch(`/observations/${row.id}/convert-to-action-plan`, { method: "POST", body: JSON.stringify({ agreed_timeline }) });
                      setSuccess("Observation converted to action plan.");
                      setError("");
                      await load();
                    } catch (err) {
                      setSuccess("");
                      setError((err as Error).message);
                    }
                  }}>Convert</button>
                ) : null}
              </div>
            )}
          />
        </div>
      </section>
      <section>
        <h2 className="mb-4 font-serif text-2xl">Linked Action Plans</h2>
        <DataTable columns={actionColumns} data={actions} />
      </section>
    </PageShell>
  );
}
