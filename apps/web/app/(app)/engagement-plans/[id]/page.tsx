"use client";

import { use, useEffect, useMemo, useState } from "react";

import { RichTextEditor } from "@/components/forms/rich-text-editor";
import { PageShell } from "@/components/layout/page-shell";
import { apiDownload, apiFetch, apiOpenFile } from "@/lib/api";
import { hasPermission } from "@/lib/auth";

type EngagementPlan = {
  id: number;
  engagement_code: string;
  audit_id: number;
  company_id: number;
  location_id: number;
  title: string;
  objective?: string | null;
  scope?: string | null;
  scope_exclusions?: string | null;
  audit_period_from?: string | null;
  audit_period_to?: string | null;
  kickoff_date?: string | null;
  planned_start_date: string;
  planned_end_date: string;
  status: string;
  lead_auditor_id?: number | null;
  reviewer_id?: number | null;
  auditee_spoc_id?: number | null;
  planned_hours?: number | null;
  approved_hours?: number | null;
};

type ChecklistItem = {
  id: number;
  check_item: string;
  is_mandatory: boolean;
  is_completed: boolean;
  remarks?: string | null;
};

type ResourceItem = {
  id: number;
  user_id: number;
  role_in_engagement: string;
  planned_hours?: number | null;
  approved_hours?: number | null;
  actual_hours?: number | null;
};

type DocumentItem = {
  id: number;
  document_type: string;
  document_id: number;
  is_latest: boolean;
};

type UserOption = { id: number; full_name: string };

const roleOptions = ["Lead Auditor", "Reviewer", "Junior Auditor", "Audit Support", "Auditee SPOC", "Observer"];
const documentTypeOptions = ["Engagement Letter", "Scope Memo", "Kickoff Minutes", "Resource Plan", "Budget Workbook", "Other"];

export default function EngagementPlanDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [tab, setTab] = useState<"overview" | "checklist" | "resources" | "documents">("overview");
  const [plan, setPlan] = useState<EngagementPlan | null>(null);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [users, setUsers] = useState<UserOption[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [resourceForm, setResourceForm] = useState({ user_id: "", role_in_engagement: "Junior Auditor", planned_hours: "", approved_hours: "", actual_hours: "" });
  const [documentType, setDocumentType] = useState("Engagement Letter");
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const canManage = hasPermission("engagement_plans:manage");
  const canApprove = hasPermission("engagement_plans:approve");

  const userLabelById = useMemo(
    () => Object.fromEntries(users.map((user) => [user.id, user.full_name])) as Record<number, string>,
    [users]
  );

  async function load() {
    const [planData, checklistData, resourceData, documentData, userData] = await Promise.all([
      apiFetch<EngagementPlan>(`/engagement-plans/${id}`),
      apiFetch<ChecklistItem[]>(`/engagement-plans/${id}/kickoff-checklist`),
      apiFetch<ResourceItem[]>(`/engagement-plans/${id}/resources`),
      apiFetch<DocumentItem[]>(`/engagement-plans/${id}/documents`),
      canManage ? apiFetch<UserOption[]>("/admin/users") : Promise.resolve([])
    ]);
    setPlan(planData);
    setChecklist(checklistData);
    setResources(resourceData);
    setDocuments(documentData);
    setUsers(userData);
  }

  useEffect(() => {
    load().catch((err) => setError((err as Error).message));
  }, [id]);

  if (!plan) return null;

  return (
    <PageShell
      title={plan.title}
      eyebrow={plan.engagement_code}
      description="Control scope, kickoff readiness, and resource budgets before audit execution begins."
    >
      {message ? <div className="rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{message}</div> : null}
      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      <div className="flex flex-wrap gap-2">
        {[
          ["overview", "Overview"],
          ["checklist", "Kickoff Checklist"],
          ["resources", "Resource Budget"],
          ["documents", "Documents"]
        ].map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={tab === value ? "button-primary" : "button-secondary"}
            onClick={() => setTab(value as typeof tab)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" ? (
        <section className="panel p-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div><span className="chip">Status</span><p className="mt-3 text-lg font-semibold">{plan.status}</p></div>
            <div><span className="chip">Audit</span><p className="mt-3 text-lg font-semibold">#{plan.audit_id}</p></div>
            <div><span className="chip">Scope</span><p className="mt-3 text-lg font-semibold">{plan.company_id} / {plan.location_id}</p></div>
          </div>
          <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <label className="space-y-2 text-sm font-semibold">
              <span>Title</span>
              <input
                className="field"
                value={plan.title}
                disabled={!canManage || !["Draft", "Rejected"].includes(plan.status)}
                onChange={(event) => setPlan((prev) => (prev ? { ...prev, title: event.target.value } : prev))}
              />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Lead Auditor</span>
              <select
                className="field"
                disabled={!canManage || !["Draft", "Rejected"].includes(plan.status)}
                value={String(plan.lead_auditor_id ?? "")}
                onChange={(event) => setPlan((prev) => (prev ? { ...prev, lead_auditor_id: event.target.value ? Number(event.target.value) : null } : prev))}
              >
                <option value="">Select Lead Auditor</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Reviewer</span>
              <select
                className="field"
                disabled={!canManage || !["Draft", "Rejected"].includes(plan.status)}
                value={String(plan.reviewer_id ?? "")}
                onChange={(event) => setPlan((prev) => (prev ? { ...prev, reviewer_id: event.target.value ? Number(event.target.value) : null } : prev))}
              >
                <option value="">Select Reviewer</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm font-semibold md:col-span-2 xl:col-span-3">
              <span>Objective</span>
              <RichTextEditor
                disabled={!canManage || !["Draft", "Rejected"].includes(plan.status)}
                value={plan.objective ?? ""}
                onChange={(nextValue) => setPlan((prev) => (prev ? { ...prev, objective: nextValue } : prev))}
                placeholder="Engagement objective"
                minHeightClass="min-h-24"
              />
            </label>
            <label className="space-y-2 text-sm font-semibold md:col-span-2 xl:col-span-3">
              <span>Scope</span>
              <RichTextEditor
                disabled={!canManage || !["Draft", "Rejected"].includes(plan.status)}
                value={plan.scope ?? ""}
                onChange={(nextValue) => setPlan((prev) => (prev ? { ...prev, scope: nextValue } : prev))}
                placeholder="Engagement scope"
                minHeightClass="min-h-24"
              />
            </label>
            <label className="space-y-2 text-sm font-semibold md:col-span-2 xl:col-span-3">
              <span>Scope Exclusions</span>
              <RichTextEditor
                disabled={!canManage || !["Draft", "Rejected"].includes(plan.status)}
                value={plan.scope_exclusions ?? ""}
                onChange={(nextValue) => setPlan((prev) => (prev ? { ...prev, scope_exclusions: nextValue } : prev))}
                placeholder="Scope exclusions"
                minHeightClass="min-h-24"
              />
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            {canManage && ["Draft", "Rejected"].includes(plan.status) ? (
              <>
                <button
                  className="button-primary"
                  onClick={async () => {
                    try {
                      await apiFetch(`/engagement-plans/${id}`, {
                        method: "PATCH",
                        body: JSON.stringify({
                          title: plan.title,
                          objective: plan.objective || null,
                          scope: plan.scope || null,
                          scope_exclusions: plan.scope_exclusions || null,
                          lead_auditor_id: plan.lead_auditor_id,
                          reviewer_id: plan.reviewer_id,
                          auditee_spoc_id: plan.auditee_spoc_id,
                          kickoff_date: plan.kickoff_date || null,
                          planned_start_date: plan.planned_start_date,
                          planned_end_date: plan.planned_end_date,
                          planned_hours: plan.planned_hours,
                          approved_hours: plan.approved_hours
                        })
                      });
                      setMessage("Engagement plan updated.");
                      setError("");
                      await load();
                    } catch (err) {
                      setMessage("");
                      setError((err as Error).message);
                    }
                  }}
                >
                  Save Draft
                </button>
                <button
                  className="button-secondary"
                  onClick={async () => {
                    try {
                      await apiFetch(`/engagement-plans/${id}/submit`, { method: "POST", body: JSON.stringify({}) });
                      setMessage("Engagement plan submitted.");
                      setError("");
                      await load();
                    } catch (err) {
                      setMessage("");
                      setError((err as Error).message);
                    }
                  }}
                >
                  Submit
                </button>
              </>
            ) : null}
            {canApprove && plan.status === "Submitted" ? (
              <>
                <button
                  className="button-primary"
                  onClick={async () => {
                    try {
                      await apiFetch(`/engagement-plans/${id}/approve`, { method: "POST", body: JSON.stringify({ remarks: null }) });
                      setMessage("Engagement plan approved.");
                      setError("");
                      await load();
                    } catch (err) {
                      setMessage("");
                      setError((err as Error).message);
                    }
                  }}
                >
                  Approve
                </button>
                <button
                  className="button-danger"
                  onClick={async () => {
                    const remarks = window.prompt("Reason for rejection") ?? "";
                    try {
                      await apiFetch(`/engagement-plans/${id}/reject`, { method: "POST", body: JSON.stringify({ remarks }) });
                      setMessage("Engagement plan rejected.");
                      setError("");
                      await load();
                    } catch (err) {
                      setMessage("");
                      setError((err as Error).message);
                    }
                  }}
                >
                  Reject
                </button>
              </>
            ) : null}
          </div>
        </section>
      ) : null}

      {tab === "checklist" ? (
        <section className="panel p-6">
          <h2 className="font-serif text-2xl">Kickoff Checklist</h2>
          <div className="mt-4 space-y-3">
            {checklist.map((item) => (
              <div key={item.id} className="rounded-2xl border border-sand bg-cream p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="flex-1 space-y-2">
                    <input
                      className="field"
                      value={item.check_item}
                      disabled={!canManage}
                      onChange={(event) => setChecklist((prev) => prev.map((entry) => (entry.id === item.id ? { ...entry, check_item: event.target.value } : entry)))}
                    />
                    <RichTextEditor
                      placeholder="Remarks"
                      disabled={!canManage}
                      value={item.remarks ?? ""}
                      onChange={(nextValue) => setChecklist((prev) => prev.map((entry) => (entry.id === item.id ? { ...entry, remarks: nextValue } : entry)))}
                      minHeightClass="min-h-20"
                    />
                  </div>
                  <div className="flex min-w-[220px] flex-col gap-3">
                    <label className="flex items-center gap-3 text-sm font-semibold">
                      <input
                        type="checkbox"
                        checked={item.is_mandatory}
                        disabled={!canManage}
                        onChange={(event) => setChecklist((prev) => prev.map((entry) => (entry.id === item.id ? { ...entry, is_mandatory: event.target.checked } : entry)))}
                      />
                      Mandatory
                    </label>
                    <label className="flex items-center gap-3 text-sm font-semibold">
                      <input
                        type="checkbox"
                        checked={item.is_completed}
                        disabled={!canManage}
                        onChange={(event) => setChecklist((prev) => prev.map((entry) => (entry.id === item.id ? { ...entry, is_completed: event.target.checked } : entry)))}
                      />
                      Completed
                    </label>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {canManage ? (
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                className="button-secondary"
                onClick={() =>
                  setChecklist((prev) => [
                    ...prev,
                    { id: -Date.now(), check_item: "", is_mandatory: true, is_completed: false, remarks: "" }
                  ])
                }
              >
                Add Checklist Item
              </button>
              <button
                className="button-primary"
                onClick={async () => {
                  try {
                    await apiFetch(`/engagement-plans/${id}/kickoff-checklist`, {
                      method: "PATCH",
                      body: JSON.stringify({
                        items: checklist.map((item) => ({
                          id: item.id > 0 ? item.id : null,
                          check_item: item.check_item,
                          is_mandatory: item.is_mandatory,
                          is_completed: item.is_completed,
                          remarks: item.remarks || null
                        }))
                      })
                    });
                    setMessage("Kickoff checklist updated.");
                    setError("");
                    await load();
                  } catch (err) {
                    setMessage("");
                    setError((err as Error).message);
                  }
                }}
              >
                Save Checklist
              </button>
            </div>
          ) : null}
        </section>
      ) : null}

      {tab === "resources" ? (
        <section className="panel p-6">
          <h2 className="font-serif text-2xl">Resource Budget</h2>
          <div className="mt-4 overflow-x-auto rounded-2xl border border-sand">
            <table className="min-w-full text-sm">
              <thead className="bg-sand/50 text-left text-xs font-semibold uppercase tracking-[0.18em] text-clay">
                <tr>
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Planned</th>
                  <th className="px-4 py-3">Approved</th>
                  <th className="px-4 py-3">Actual</th>
                  {canManage ? <th className="px-4 py-3">Actions</th> : null}
                </tr>
              </thead>
              <tbody>
                {resources.map((resource) => (
                  <tr key={resource.id} className="border-t border-sand bg-cream">
                    <td className="px-4 py-3">{userLabelById[resource.user_id] ?? `User #${resource.user_id}`}</td>
                    <td className="px-4 py-3">
                      {canManage ? (
                        <select
                          className="field"
                          value={resource.role_in_engagement}
                          onChange={(event) => setResources((prev) => prev.map((entry) => (entry.id === resource.id ? { ...entry, role_in_engagement: event.target.value } : entry)))}
                        >
                          {roleOptions.map((option) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                      ) : (
                        resource.role_in_engagement
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {canManage ? (
                        <input className="field" type="number" min="0" step="0.5" value={resource.planned_hours ?? ""} onChange={(event) => setResources((prev) => prev.map((entry) => (entry.id === resource.id ? { ...entry, planned_hours: event.target.value ? Number(event.target.value) : null } : entry)))} />
                      ) : (
                        resource.planned_hours ?? "--"
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {canManage ? (
                        <input className="field" type="number" min="0" step="0.5" value={resource.approved_hours ?? ""} onChange={(event) => setResources((prev) => prev.map((entry) => (entry.id === resource.id ? { ...entry, approved_hours: event.target.value ? Number(event.target.value) : null } : entry)))} />
                      ) : (
                        resource.approved_hours ?? "--"
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {canManage ? (
                        <input className="field" type="number" min="0" step="0.5" value={resource.actual_hours ?? ""} onChange={(event) => setResources((prev) => prev.map((entry) => (entry.id === resource.id ? { ...entry, actual_hours: event.target.value ? Number(event.target.value) : null } : entry)))} />
                      ) : (
                        resource.actual_hours ?? "--"
                      )}
                    </td>
                    {canManage ? (
                      <td className="px-4 py-3">
                        <button
                          className="button-secondary px-4 py-2"
                          onClick={async () => {
                            try {
                              await apiFetch(`/engagement-plans/${id}/resources/${resource.id}`, {
                                method: "PATCH",
                                body: JSON.stringify({
                                  role_in_engagement: resource.role_in_engagement,
                                  planned_hours: resource.planned_hours,
                                  approved_hours: resource.approved_hours,
                                  actual_hours: resource.actual_hours
                                })
                              });
                              setMessage("Resource updated.");
                              setError("");
                              await load();
                            } catch (err) {
                              setMessage("");
                              setError((err as Error).message);
                            }
                          }}
                        >
                          Save
                        </button>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {canManage ? (
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              <select className="field" value={resourceForm.user_id} onChange={(event) => setResourceForm((prev) => ({ ...prev, user_id: event.target.value }))}>
                <option value="">Select User</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </select>
              <select className="field" value={resourceForm.role_in_engagement} onChange={(event) => setResourceForm((prev) => ({ ...prev, role_in_engagement: event.target.value }))}>
                {roleOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <input className="field" type="number" min="0" step="0.5" placeholder="Planned" value={resourceForm.planned_hours} onChange={(event) => setResourceForm((prev) => ({ ...prev, planned_hours: event.target.value }))} />
              <input className="field" type="number" min="0" step="0.5" placeholder="Approved" value={resourceForm.approved_hours} onChange={(event) => setResourceForm((prev) => ({ ...prev, approved_hours: event.target.value }))} />
              <button
                className="button-primary"
                onClick={async () => {
                  try {
                    await apiFetch(`/engagement-plans/${id}/resources`, {
                      method: "POST",
                      body: JSON.stringify({
                        user_id: Number(resourceForm.user_id),
                        role_in_engagement: resourceForm.role_in_engagement,
                        planned_hours: resourceForm.planned_hours ? Number(resourceForm.planned_hours) : null,
                        approved_hours: resourceForm.approved_hours ? Number(resourceForm.approved_hours) : null,
                        actual_hours: resourceForm.actual_hours ? Number(resourceForm.actual_hours) : null
                      })
                    });
                    setResourceForm({ user_id: "", role_in_engagement: "Junior Auditor", planned_hours: "", approved_hours: "", actual_hours: "" });
                    setMessage("Resource added.");
                    setError("");
                    await load();
                  } catch (err) {
                    setMessage("");
                    setError((err as Error).message);
                  }
                }}
              >
                Add Resource
              </button>
            </div>
          ) : null}
        </section>
      ) : null}

      {tab === "documents" ? (
        <section className="panel p-6">
          <h2 className="font-serif text-2xl">Engagement Documents</h2>
          <p className="mt-2 text-sm text-slate">
            Upload the Engagement Letter here as part of kickoff readiness. The system treats it as recommended guidance for now, so later audit work is not hard-blocked if it is still pending.
          </p>
          {canManage ? (
            <div className="mt-4 grid gap-3 md:grid-cols-[220px_1fr_auto]">
              <select className="field" value={documentType} onChange={(event) => setDocumentType(event.target.value)}>
                {documentTypeOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <input className="field" type="file" onChange={(event) => setDocumentFile(event.target.files?.[0] ?? null)} />
              <button
                className="button-primary"
                onClick={async () => {
                  if (!documentFile) return;
                  try {
                    const formData = new FormData();
                    formData.append("document_type", documentType);
                    formData.append("file", documentFile);
                    await apiFetch(`/engagement-plans/${id}/documents`, {
                      method: "POST",
                      body: formData
                    });
                    setDocumentFile(null);
                    setMessage("Document uploaded.");
                    setError("");
                    await load();
                  } catch (err) {
                    setMessage("");
                    setError((err as Error).message);
                  }
                }}
              >
                Upload
              </button>
            </div>
          ) : null}
          <div className="mt-4 overflow-x-auto rounded-2xl border border-sand">
            <table className="min-w-full text-sm">
              <thead className="bg-sand/50 text-left text-xs font-semibold uppercase tracking-[0.18em] text-clay">
                <tr>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Document ID</th>
                  <th className="px-4 py-3">Latest</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((document) => (
                  <tr key={document.id} className="border-t border-sand bg-cream">
                    <td className="px-4 py-3">{document.document_type}</td>
                    <td className="px-4 py-3">#{document.document_id}</td>
                    <td className="px-4 py-3">{document.is_latest ? "Yes" : "No"}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button className="button-secondary px-4 py-2" onClick={() => apiOpenFile(`/engagement-plans/documents/${document.id}/view`)}>
                          View File
                        </button>
                        <button
                          className="button-secondary px-4 py-2"
                          onClick={() => apiDownload(`/engagement-plans/documents/${document.id}/download`, `${document.document_type}-${document.id}`)}
                        >
                          Download
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!documents.length ? (
                  <tr className="border-t border-sand bg-cream">
                    <td className="px-4 py-6 text-sm text-slate" colSpan={4}>
                      No engagement documents uploaded yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </PageShell>
  );
}
