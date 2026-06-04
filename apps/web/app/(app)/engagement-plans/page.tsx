"use client";

import Link from "next/link";
import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";

import { AsyncLookupField } from "@/components/forms/async-lookup";
import { RichTextEditor } from "@/components/forms/rich-text-editor";
import { PageShell } from "@/components/layout/page-shell";
import { DataTable } from "@/components/table/data-table";
import { apiFetch } from "@/lib/api";
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

type AuditOption = { id: number; audit_number: string; audit_name: string; audit_owner_id?: number | null };
type EngagementPrefill = {
  audit_id: number;
  audit_number: string;
  audit_name: string;
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
  lead_auditor_id?: number | null;
  lead_auditor_name?: string | null;
  reviewer_id?: number | null;
  reviewer_name?: string | null;
  auditee_spoc_auditee_id?: number | null;
  auditee_spoc_id?: number | null;
  auditee_spoc_name?: string | null;
  planned_hours?: number | null;
  approved_hours?: number | null;
  can_create: boolean;
  existing_engagement_plan_id?: number | null;
};

const emptyForm = {
  audit_id: "",
  title: "",
  objective: "",
  scope: "",
  scope_exclusions: "",
  audit_period_from: "",
  audit_period_to: "",
  kickoff_date: "",
  planned_start_date: "",
  planned_end_date: "",
  lead_auditor_id: "",
  lead_auditor_label: "",
  reviewer_id: "",
  reviewer_label: "",
  auditee_spoc_auditee_id: "",
  auditee_spoc_id: "",
  auditee_spoc_label: "",
  planned_hours: "",
  approved_hours: ""
};

function toNumber(value: string) {
  return value ? Number(value) : null;
}

function toNumberOrUndefined(value: string) {
  return value ? Number(value) : undefined;
}

export default function EngagementPlansPage() {
  const [items, setItems] = useState<EngagementPlan[]>([]);
  const [audits, setAudits] = useState<AuditOption[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [search, setSearch] = useState("");
  const [prefillMessage, setPrefillMessage] = useState("");
  const [existingEngagementId, setExistingEngagementId] = useState<number | null>(null);
  const [prefillLoading, setPrefillLoading] = useState(false);
  const canManage = hasPermission("engagement_plans:manage");
  const canApprove = hasPermission("engagement_plans:approve");

  const auditLabelById = useMemo(
    () =>
      Object.fromEntries(
        audits.map((audit) => [audit.id, `${audit.audit_number} - ${audit.audit_name}`])
      ) as Record<number, string>,
    [audits]
  );
  const columns = useMemo<ColumnDef<EngagementPlan>[]>(
    () => [
      { accessorKey: "engagement_code", header: "Engagement Code" },
      { accessorKey: "title", header: "Title" },
      { accessorKey: "status", header: "Status" },
      {
        accessorKey: "audit_id",
        header: "Audit",
        cell: ({ row }) => auditLabelById[row.original.audit_id] ?? `#${row.original.audit_id}`
      },
      { accessorKey: "planned_start_date", header: "Planned Start" },
      { accessorKey: "planned_end_date", header: "Planned End" }
    ],
    [auditLabelById]
  );

  async function load() {
    const listPromise = apiFetch<{ items: EngagementPlan[] }>(`/engagement-plans?page_size=100${search ? `&search=${encodeURIComponent(search)}` : ""}`);
    const auditPromise = apiFetch<{ items: AuditOption[] }>("/audits?page_size=100&scope=mine");
    const [listData, auditData] = await Promise.all([listPromise, auditPromise]);
    setItems(listData.items);
    setAudits(auditData.items);
  }

  function applyPrefill(prefill: EngagementPrefill) {
    setForm({
      audit_id: String(prefill.audit_id),
      title: prefill.title ?? "",
      objective: prefill.objective ?? "",
      scope: prefill.scope ?? "",
      scope_exclusions: prefill.scope_exclusions ?? "",
      audit_period_from: prefill.audit_period_from ?? "",
      audit_period_to: prefill.audit_period_to ?? "",
      kickoff_date: prefill.kickoff_date ?? "",
      planned_start_date: prefill.planned_start_date ?? "",
      planned_end_date: prefill.planned_end_date ?? "",
      lead_auditor_id: prefill.lead_auditor_id ? String(prefill.lead_auditor_id) : "",
      lead_auditor_label: prefill.lead_auditor_name ?? "",
      reviewer_id: prefill.reviewer_id ? String(prefill.reviewer_id) : "",
      reviewer_label: prefill.reviewer_name ?? "",
      auditee_spoc_auditee_id: prefill.auditee_spoc_auditee_id ? String(prefill.auditee_spoc_auditee_id) : "",
      auditee_spoc_id: prefill.auditee_spoc_id ? String(prefill.auditee_spoc_id) : "",
      auditee_spoc_label: prefill.auditee_spoc_name ?? "",
      planned_hours: prefill.planned_hours != null ? String(prefill.planned_hours) : "",
      approved_hours: prefill.approved_hours != null ? String(prefill.approved_hours) : ""
    });
    setExistingEngagementId(prefill.existing_engagement_plan_id ?? null);
    setPrefillMessage(
      prefill.can_create
        ? `Draft values loaded from ${prefill.audit_number} - ${prefill.audit_name}. You can refine them before saving.`
        : `An engagement plan already exists for ${prefill.audit_number} - ${prefill.audit_name}. Open the existing record instead of creating a duplicate.`
    );
  }

  async function loadPrefill(auditId: string) {
    if (!auditId) {
      setForm(emptyForm);
      setExistingEngagementId(null);
      setPrefillMessage("");
      return;
    }
    setPrefillLoading(true);
    try {
      const prefill = await apiFetch<EngagementPrefill>(`/engagement-plans/prefill/${auditId}`);
      applyPrefill(prefill);
      setError("");
    } catch (err) {
      setExistingEngagementId(null);
      setPrefillMessage("");
      setError((err as Error).message);
      setForm((prev) => ({ ...prev, audit_id: auditId }));
    } finally {
      setPrefillLoading(false);
    }
  }

  useEffect(() => {
    load().catch((err) => setError((err as Error).message));
  }, [search]);

  useEffect(() => {
    if (typeof window === "undefined" || !canManage) return;
    const auditId = new URLSearchParams(window.location.search).get("auditId");
    if (!auditId) return;
    loadPrefill(auditId).catch((err) => setError((err as Error).message));
  }, [canManage]);

  return (
    <PageShell
      title="Engagement Planning"
      eyebrow="Fieldwork Readiness"
      description="Formalize scope, kickoff, staffing, and budget control before execution begins."
      actions={<input className="field min-w-60" placeholder="Search engagement plans" value={search} onChange={(event) => setSearch(event.target.value)} />}
    >
      {canManage ? (
        <section className="panel p-4 xl:p-5">
          <h2 className="font-serif text-xl xl:text-2xl">Create Engagement Plan</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <label className="space-y-2 text-sm font-semibold">
              <span>Audit</span>
              <select className="field" value={form.audit_id} onChange={(event) => void loadPrefill(event.target.value)}>
                <option value="">Select Audit</option>
                {audits.map((audit) => (
                  <option key={audit.id} value={audit.id}>
                    {audit.audit_number} - {audit.audit_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Title</span>
              <input className="field" value={form.title} onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))} />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Lead Auditor</span>
              <AsyncLookupField
                value={form.lead_auditor_id}
                selectedLabel={form.lead_auditor_label}
                disabled={!canApprove}
                endpoint="/admin/users"
                queryParam="q"
                placeholder="Search Lead Auditor"
                staticParams={{ active_only: true, roles: "super_admin,head_auditor,auditor" }}
                mapOption={(row) => ({
                  value: row.id as number,
                  label: String(row.full_name ?? row.username ?? row.id),
                  description: [row.designation_title, row.company_name, row.location_label].filter(Boolean).join(" - ")
                })}
                onSelect={(option) => setForm((prev) => ({
                  ...prev,
                  lead_auditor_id: option ? String(option.value) : "",
                  lead_auditor_label: option?.label ?? ""
                }))}
              />
            </label>
            <label className="space-y-2 text-sm font-semibold md:col-span-2 xl:col-span-3">
              <span>Objective</span>
              <RichTextEditor value={form.objective} onChange={(nextValue) => setForm((prev) => ({ ...prev, objective: nextValue }))} placeholder="Engagement objective" minHeightClass="min-h-24" />
            </label>
            <label className="space-y-2 text-sm font-semibold md:col-span-2 xl:col-span-3">
              <span>Scope</span>
              <RichTextEditor value={form.scope} onChange={(nextValue) => setForm((prev) => ({ ...prev, scope: nextValue }))} placeholder="Engagement scope" minHeightClass="min-h-24" />
            </label>
            <label className="space-y-2 text-sm font-semibold md:col-span-2 xl:col-span-3">
              <span>Scope Exclusions</span>
              <RichTextEditor value={form.scope_exclusions} onChange={(nextValue) => setForm((prev) => ({ ...prev, scope_exclusions: nextValue }))} placeholder="Scope exclusions" minHeightClass="min-h-24" />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Audit Period From</span>
              <input type="date" className="field" value={form.audit_period_from} onChange={(event) => setForm((prev) => ({ ...prev, audit_period_from: event.target.value }))} />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Audit Period To</span>
              <input type="date" className="field" value={form.audit_period_to} onChange={(event) => setForm((prev) => ({ ...prev, audit_period_to: event.target.value }))} />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Kickoff Date</span>
              <input type="date" className="field" value={form.kickoff_date} onChange={(event) => setForm((prev) => ({ ...prev, kickoff_date: event.target.value }))} />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Planned Start</span>
              <input type="date" className="field" value={form.planned_start_date} onChange={(event) => setForm((prev) => ({ ...prev, planned_start_date: event.target.value }))} />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Planned End</span>
              <input type="date" className="field" value={form.planned_end_date} onChange={(event) => setForm((prev) => ({ ...prev, planned_end_date: event.target.value }))} />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Reviewer</span>
              <AsyncLookupField
                value={form.reviewer_id}
                selectedLabel={form.reviewer_label}
                endpoint="/admin/users"
                queryParam="q"
                placeholder="Search Reviewer"
                staticParams={{ active_only: true, roles: "super_admin,head_auditor,auditor,management" }}
                mapOption={(row) => ({
                  value: row.id as number,
                  label: String(row.full_name ?? row.username ?? row.id),
                  description: [row.designation_title, row.company_name, row.location_label].filter(Boolean).join(" - ")
                })}
                onSelect={(option) => setForm((prev) => ({
                  ...prev,
                  reviewer_id: option ? String(option.value) : "",
                  reviewer_label: option?.label ?? ""
                }))}
              />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Auditee SPOC</span>
              <AsyncLookupField
                value={form.auditee_spoc_auditee_id}
                selectedLabel={form.auditee_spoc_label}
                endpoint="/master/auditees"
                queryParam="search"
                placeholder="Search Auditee SPOC"
                staticParams={{ is_active: true }}
                mapOption={(row) => ({
                  value: row.id as number,
                  label: String(row.full_name ?? row.auditee_code ?? row.id),
                  description: [row.auditee_code, row.designation, row.department].filter(Boolean).join(" - ")
                })}
                onSelect={(option) => setForm((prev) => ({
                  ...prev,
                  auditee_spoc_auditee_id: option ? String(option.value) : "",
                  auditee_spoc_label: option?.label ?? "",
                  auditee_spoc_id: ""
                }))}
              />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Planned Hours</span>
              <input type="number" min="0" step="0.5" className="field" value={form.planned_hours} onChange={(event) => setForm((prev) => ({ ...prev, planned_hours: event.target.value }))} />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Approved Hours</span>
              <input type="number" min="0" step="0.5" className="field" value={form.approved_hours} onChange={(event) => setForm((prev) => ({ ...prev, approved_hours: event.target.value }))} />
            </label>
          </div>
          {prefillMessage ? (
            <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl bg-ivory px-4 py-3 text-sm text-slate">
              <span>{prefillMessage}</span>
              {existingEngagementId ? (
                <Link href={`/engagement-plans/${existingEngagementId}`} className="button-secondary px-4 py-2">
                  Open Existing
                </Link>
              ) : null}
            </div>
          ) : null}
          <div className="mt-4 rounded-2xl border border-sand bg-cream px-4 py-3 text-sm text-slate">
            Upload the Engagement Letter in the document tab after saving the draft. This is recommended guidance for the Lead Auditor, but it does not block later audit work.
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              className="button-primary"
              disabled={prefillLoading || !!existingEngagementId}
              onClick={async () => {
                try {
                  await apiFetch("/engagement-plans", {
                    method: "POST",
                    body: JSON.stringify({
                      audit_id: Number(form.audit_id),
                      title: form.title,
                      objective: form.objective || null,
                      scope: form.scope || null,
                      scope_exclusions: form.scope_exclusions || null,
                      audit_period_from: form.audit_period_from || null,
                      audit_period_to: form.audit_period_to || null,
                      kickoff_date: form.kickoff_date || null,
                      planned_start_date: form.planned_start_date,
                      planned_end_date: form.planned_end_date,
                      lead_auditor_id: toNumber(form.lead_auditor_id),
                      reviewer_id: toNumber(form.reviewer_id),
                      auditee_spoc_auditee_id: toNumber(form.auditee_spoc_auditee_id),
                      planned_hours: toNumberOrUndefined(form.planned_hours),
                      approved_hours: toNumberOrUndefined(form.approved_hours)
                    })
                  });
                  setForm(emptyForm);
                  setSuccess("Engagement plan created.");
                  setError("");
                  await load();
                } catch (err) {
                  setSuccess("");
                  setError((err as Error).message);
                }
              }}
            >
              {prefillLoading ? "Loading..." : "Save"}
            </button>
            <p className="text-sm text-slate">The selected audit now preloads dates, ownership, and starter scope so the assigned Lead Auditor can begin faster.</p>
          </div>
        </section>
      ) : null}
      {success ? <div className="rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{success}</div> : null}
      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      <DataTable
        columns={columns}
        data={items}
        renderRowActions={(row) => (
          <div className="flex flex-wrap gap-2">
            <Link href={`/engagement-plans/${row.id}`} className="button-secondary px-4 py-2">
              Open
            </Link>
            {canManage && (row.status === "Draft" || row.status === "Rejected") ? (
              <button
                type="button"
                className="button-secondary px-4 py-2"
                onClick={async () => {
                  try {
                    await apiFetch(`/engagement-plans/${row.id}/submit`, { method: "POST", body: JSON.stringify({}) });
                    setSuccess("Engagement plan submitted.");
                    setError("");
                    await load();
                  } catch (err) {
                    setSuccess("");
                    setError((err as Error).message);
                  }
                }}
              >
                Submit
              </button>
            ) : null}
            {canApprove && row.status === "Submitted" ? (
              <>
                <button
                  type="button"
                  className="button-secondary px-4 py-2"
                  onClick={async () => {
                    try {
                      await apiFetch(`/engagement-plans/${row.id}/approve`, { method: "POST", body: JSON.stringify({ remarks: null }) });
                      setSuccess("Engagement plan approved.");
                      setError("");
                      await load();
                    } catch (err) {
                      setSuccess("");
                      setError((err as Error).message);
                    }
                  }}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="button-danger"
                  onClick={async () => {
                    const remarks = window.prompt("Reason for rejection") ?? "";
                    try {
                      await apiFetch(`/engagement-plans/${row.id}/reject`, { method: "POST", body: JSON.stringify({ remarks }) });
                      setSuccess("Engagement plan rejected.");
                      setError("");
                      await load();
                    } catch (err) {
                      setSuccess("");
                      setError((err as Error).message);
                    }
                  }}
                >
                  Reject
                </button>
              </>
            ) : null}
          </div>
        )}
      />
    </PageShell>
  );
}
