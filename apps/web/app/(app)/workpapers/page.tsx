"use client";

import Link from "next/link";
import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { DataTable } from "@/components/table/data-table";
import { apiFetch } from "@/lib/api";
import { getSessionUser, hasPermission } from "@/lib/auth";

type AuditOption = { id: number; audit_number: string; audit_name: string };
type AuditMember = { id: number; user_id: number; user_name?: string | null; role_on_audit: string };
type ActivityOption = { id: number; title: string };
type ObservationOption = { id: number; observation_number: string; heading: string };
type Workpaper = {
  id: number;
  workpaper_code: string;
  audit_id: number;
  activity_id?: number | null;
  observation_id?: number | null;
  test_procedure_id?: number | null;
  title: string;
  folder_path?: string | null;
  status: string;
  current_version_no: number;
  owner_user_id?: number | null;
  owner_name?: string | null;
  reviewer_user_id?: number | null;
  reviewer_name?: string | null;
  signoff_at?: string | null;
};
type UserOption = { id: number; label: string };

const emptyForm = {
  audit_id: "",
  activity_id: "",
  observation_id: "",
  title: "",
  folder_path: "",
  owner_user_id: "",
  reviewer_user_id: "",
  test_procedure_id: "",
};

function uniqueUsers(members: AuditMember[]): UserOption[] {
  const session = getSessionUser();
  const seen = new Set<number>();
  const options: UserOption[] = [];
  for (const member of members) {
    if (seen.has(member.user_id)) continue;
    seen.add(member.user_id);
    const roleLabel = member.role_on_audit.replaceAll("_", " ");
    const selfSuffix = session?.id === member.user_id ? " (You)" : "";
    options.push({ id: member.user_id, label: `${member.user_name ?? `User #${member.user_id}`} - ${roleLabel}${selfSuffix}` });
  }
  return options;
}

export default function WorkpapersPage() {
  const [items, setItems] = useState<Workpaper[]>([]);
  const [audits, setAudits] = useState<AuditOption[]>([]);
  const [members, setMembers] = useState<UserOption[]>([]);
  const [activities, setActivities] = useState<ActivityOption[]>([]);
  const [observations, setObservations] = useState<ObservationOption[]>([]);
  const [selectedAuditId, setSelectedAuditId] = useState("");
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const canManage = hasPermission("workpapers:manage");

  const auditLabelById = useMemo(
    () =>
      Object.fromEntries(audits.map((audit) => [audit.id, `${audit.audit_number} - ${audit.audit_name}`])) as Record<number, string>,
    [audits]
  );
  const userLabelById = useMemo(
    () => Object.fromEntries(members.map((member) => [member.id, member.label])) as Record<number, string>,
    [members]
  );
  const activityLabelById = useMemo(
    () => Object.fromEntries(activities.map((activity) => [activity.id, activity.title])) as Record<number, string>,
    [activities]
  );
  const observationLabelById = useMemo(
    () =>
      Object.fromEntries(
        observations.map((observation) => [observation.id, `${observation.observation_number} - ${observation.heading}`])
      ) as Record<number, string>,
    [observations]
  );

  const columns = useMemo<ColumnDef<Workpaper>[]>(
    () => [
      { accessorKey: "workpaper_code", header: "Workpaper Code" },
      { accessorKey: "title", header: "Title" },
      {
        accessorKey: "audit_id",
        header: "Audit",
        cell: ({ row }) => auditLabelById[row.original.audit_id] ?? `#${row.original.audit_id}`,
      },
      {
        accessorKey: "activity_id",
        header: "Activity",
        cell: ({ row }) => (row.original.activity_id ? activityLabelById[row.original.activity_id] ?? `#${row.original.activity_id}` : "--"),
      },
      { accessorKey: "status", header: "Status" },
      { accessorKey: "current_version_no", header: "Version" },
      {
        accessorKey: "owner_user_id",
        header: "Owner",
        cell: ({ row }) => row.original.owner_name ?? (row.original.owner_user_id ? userLabelById[row.original.owner_user_id] ?? `User #${row.original.owner_user_id}` : "--"),
      },
      {
        accessorKey: "reviewer_user_id",
        header: "Reviewer",
        cell: ({ row }) => row.original.reviewer_name ?? (row.original.reviewer_user_id ? userLabelById[row.original.reviewer_user_id] ?? `User #${row.original.reviewer_user_id}` : "--"),
      },
    ],
    [activityLabelById, auditLabelById, userLabelById]
  );

  async function load() {
    const [workpaperData, auditData] = await Promise.all([
      apiFetch<{ items: Workpaper[] }>(
        `/workpapers?page_size=100${selectedAuditId ? `&audit_id=${selectedAuditId}` : ""}${search ? `&search=${encodeURIComponent(search)}` : ""}`
      ),
      apiFetch<{ items: AuditOption[] }>("/audits?page_size=100&scope=mine"),
    ]);
    setItems(workpaperData.items);
    setAudits(auditData.items);
  }

  async function loadAuditContext(auditId: string) {
    if (!auditId) {
      setMembers([]);
      setActivities([]);
      setObservations([]);
      return;
    }
    const [memberData, activityData, observationData] = await Promise.all([
      apiFetch<AuditMember[]>(`/audits/${auditId}/members`),
      apiFetch<{ items: ActivityOption[] }>(`/audits/${auditId}/activities?page_size=100`),
      apiFetch<{ items: ObservationOption[] }>(`/audits/${auditId}/observations?page_size=100`),
    ]);
    setMembers(uniqueUsers(memberData));
    setActivities(activityData.items);
    setObservations(observationData.items);
  }

  useEffect(() => {
    if (typeof window === "undefined") return;
    const auditId = new URLSearchParams(window.location.search).get("audit_id") ?? "";
    setSelectedAuditId(auditId);
    setForm((prev) => ({ ...prev, audit_id: prev.audit_id || auditId }));
  }, []);

  useEffect(() => {
    load().catch((err) => setError((err as Error).message));
  }, [search, selectedAuditId]);

  useEffect(() => {
    loadAuditContext(form.audit_id).catch((err) => setError((err as Error).message));
  }, [form.audit_id]);

  return (
    <PageShell
      title="Workpapers"
      eyebrow="Fieldwork Library"
      description="Maintain versioned workpapers, route them for review, and lock final sign-offs without losing history."
      actions={
        <div className="flex w-full flex-col gap-2 sm:flex-row">
          <select className="field min-w-56" value={selectedAuditId} onChange={(event) => setSelectedAuditId(event.target.value)}>
            <option value="">All audits</option>
            {audits.map((audit) => (
              <option key={audit.id} value={audit.id}>
                {audit.audit_number} - {audit.audit_name}
              </option>
            ))}
          </select>
          <input className="field min-w-56" placeholder="Search workpapers" value={search} onChange={(event) => setSearch(event.target.value)} />
        </div>
      }
    >
      {canManage ? (
        <section className="panel p-6">
          <h2 className="font-serif text-2xl">Create Workpaper</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <label className="space-y-2 text-sm font-semibold">
              <span>Audit</span>
              <select
                className="field"
                value={form.audit_id}
                onChange={(event) => {
                  const value = event.target.value;
                  setForm((prev) => ({
                    ...prev,
                    audit_id: value,
                    activity_id: "",
                    observation_id: "",
                    owner_user_id: "",
                    reviewer_user_id: "",
                  }));
                }}
              >
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
              <span>Folder Path</span>
              <input className="field" placeholder="/Fieldwork/Revenue" value={form.folder_path} onChange={(event) => setForm((prev) => ({ ...prev, folder_path: event.target.value }))} />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Activity</span>
              <select className="field" disabled={!form.audit_id} value={form.activity_id} onChange={(event) => setForm((prev) => ({ ...prev, activity_id: event.target.value }))}>
                <option value="">{form.audit_id ? "Select Activity" : "Select Audit first"}</option>
                {activities.map((activity) => (
                  <option key={activity.id} value={activity.id}>
                    {activity.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Observation</span>
              <select className="field" disabled={!form.audit_id} value={form.observation_id} onChange={(event) => setForm((prev) => ({ ...prev, observation_id: event.target.value }))}>
                <option value="">{form.audit_id ? "Select Observation" : "Select Audit first"}</option>
                {observations.map((observation) => (
                  <option key={observation.id} value={observation.id}>
                    {observation.observation_number} - {observation.heading}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Test Procedure Ref</span>
              <input className="field" type="number" min="1" placeholder="Optional future hook" value={form.test_procedure_id} onChange={(event) => setForm((prev) => ({ ...prev, test_procedure_id: event.target.value }))} />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Owner</span>
              <select className="field" disabled={!form.audit_id} value={form.owner_user_id} onChange={(event) => setForm((prev) => ({ ...prev, owner_user_id: event.target.value }))}>
                <option value="">{form.audit_id ? "Select Owner" : "Select Audit first"}</option>
                {members.map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Reviewer</span>
              <select className="field" disabled={!form.audit_id} value={form.reviewer_user_id} onChange={(event) => setForm((prev) => ({ ...prev, reviewer_user_id: event.target.value }))}>
                <option value="">{form.audit_id ? "Select Reviewer" : "Select Audit first"}</option>
                {members.map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              className="button-primary"
              onClick={async () => {
                try {
                  await apiFetch("/workpapers", {
                    method: "POST",
                    body: JSON.stringify({
                      audit_id: Number(form.audit_id),
                      activity_id: form.activity_id ? Number(form.activity_id) : null,
                      observation_id: form.observation_id ? Number(form.observation_id) : null,
                      test_procedure_id: form.test_procedure_id ? Number(form.test_procedure_id) : null,
                      title: form.title,
                      folder_path: form.folder_path || null,
                      owner_user_id: form.owner_user_id ? Number(form.owner_user_id) : null,
                      reviewer_user_id: form.reviewer_user_id ? Number(form.reviewer_user_id) : null,
                    }),
                  });
                  setForm({ ...emptyForm, audit_id: form.audit_id });
                  setSuccess("Workpaper created.");
                  setError("");
                  await load();
                } catch (err) {
                  setSuccess("");
                  setError((err as Error).message);
                }
              }}
            >
              Save
            </button>
            <p className="text-sm text-slate">Upload the first version from the detail page so review history and version numbers stay clean.</p>
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
            <Link href={`/workpapers/${row.id}`} className="button-secondary px-4 py-2">
              Open
            </Link>
            {canManage && row.status === "Draft" ? (
              <button
                type="button"
                className="button-secondary px-4 py-2"
                onClick={async () => {
                  try {
                    await apiFetch(`/workpapers/${row.id}/submit-review`, {
                      method: "POST",
                      body: JSON.stringify({ comment: null }),
                    });
                    setSuccess("Workpaper submitted for review.");
                    setError("");
                    await load();
                  } catch (err) {
                    setSuccess("");
                    setError((err as Error).message);
                  }
                }}
              >
                Submit Review
              </button>
            ) : null}
          </div>
        )}
      />
    </PageShell>
  );
}
