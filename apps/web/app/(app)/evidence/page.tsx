"use client";

import Link from "next/link";
import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";

import { RichTextEditor } from "@/components/forms/rich-text-editor";
import { PageShell } from "@/components/layout/page-shell";
import { DataTable } from "@/components/table/data-table";
import { apiDownload, apiFetch, apiOpenFile } from "@/lib/api";
import { hasPermission } from "@/lib/auth";

type AuditOption = { id: number; audit_number: string; audit_name: string };
type ActivityOption = { id: number; title: string };
type EvidenceItem = {
  id: number;
  evidence_code: string;
  audit_id: number;
  activity_id?: number | null;
  source_type: string;
  source_name: string;
  evidence_description?: string | null;
  confidentiality_level: string;
  collected_at: string;
};

const confidentialityOptions = ["Internal", "Confidential", "Restricted", "Highly Restricted"];

export default function EvidenceRegisterPage() {
  const [audits, setAudits] = useState<AuditOption[]>([]);
  const [activities, setActivities] = useState<ActivityOption[]>([]);
  const [items, setItems] = useState<EvidenceItem[]>([]);
  const [auditId, setAuditId] = useState("");
  const [search, setSearch] = useState("");
  const [sourceType, setSourceType] = useState("Walkthrough");
  const [sourceName, setSourceName] = useState("");
  const [evidenceDescription, setEvidenceDescription] = useState("");
  const [activityId, setActivityId] = useState("");
  const [confidentialityLevel, setConfidentialityLevel] = useState("Internal");
  const [file, setFile] = useState<File | null>(null);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const canManage = hasPermission("evidence:manage");

  const auditLabelById = useMemo(
    () => Object.fromEntries(audits.map((audit) => [audit.id, `${audit.audit_number} - ${audit.audit_name}`])) as Record<number, string>,
    [audits]
  );
  const activityLabelById = useMemo(
    () => Object.fromEntries(activities.map((activity) => [activity.id, activity.title])) as Record<number, string>,
    [activities]
  );
  const columns = useMemo<ColumnDef<EvidenceItem>[]>(
    () => [
      { accessorKey: "evidence_code", header: "Evidence Code" },
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
      { accessorKey: "source_type", header: "Source Type" },
      { accessorKey: "source_name", header: "Source Name" },
      { accessorKey: "confidentiality_level", header: "Confidentiality" },
      { accessorKey: "collected_at", header: "Collected At" },
    ],
    [activityLabelById, auditLabelById]
  );

  async function load() {
    const [listData, auditData] = await Promise.all([
      apiFetch<{ items: EvidenceItem[] }>(`/evidence?page_size=100${auditId ? `&audit_id=${auditId}` : ""}${search ? `&search=${encodeURIComponent(search)}` : ""}`),
      apiFetch<{ items: AuditOption[] }>("/audits?page_size=100&scope=mine"),
    ]);
    setItems(listData.items);
    setAudits(auditData.items);
  }

  async function loadActivities(nextAuditId: string) {
    if (!nextAuditId) {
      setActivities([]);
      return;
    }
    const activityData = await apiFetch<{ items: ActivityOption[] }>(`/audits/${nextAuditId}/activities?page_size=100`);
    setActivities(activityData.items);
  }

  useEffect(() => {
    if (typeof window === "undefined") return;
    const initialAuditId = new URLSearchParams(window.location.search).get("audit_id") ?? "";
    setAuditId(initialAuditId);
  }, []);

  useEffect(() => {
    load().catch((err) => setError((err as Error).message));
  }, [auditId, search]);

  useEffect(() => {
    loadActivities(auditId).catch((err) => setError((err as Error).message));
  }, [auditId]);

  return (
    <PageShell
      title="Evidence Register"
      eyebrow="Evidence Control"
      description="Register supporting evidence once, then link it cleanly across workpapers, findings, and future testing modules."
      actions={
        <div className="flex w-full flex-col gap-2 sm:flex-row">
          <select className="field min-w-56" value={auditId} onChange={(event) => { setAuditId(event.target.value); setActivityId(""); }}>
            <option value="">All audits</option>
            {audits.map((audit) => (
              <option key={audit.id} value={audit.id}>
                {audit.audit_number} - {audit.audit_name}
              </option>
            ))}
          </select>
          <input className="field min-w-56" placeholder="Search evidence" value={search} onChange={(event) => setSearch(event.target.value)} />
        </div>
      }
    >
      {canManage ? (
        <section className="panel p-6">
          <h2 className="font-serif text-2xl">Register Evidence</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <label className="space-y-2 text-sm font-semibold">
              <span>Audit</span>
              <select className="field" value={auditId} onChange={(event) => { setAuditId(event.target.value); setActivityId(""); }}>
                <option value="">Select Audit</option>
                {audits.map((audit) => (
                  <option key={audit.id} value={audit.id}>
                    {audit.audit_number} - {audit.audit_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Activity</span>
              <select className="field" disabled={!auditId} value={activityId} onChange={(event) => setActivityId(event.target.value)}>
                <option value="">{auditId ? "Select Activity" : "Select Audit first"}</option>
                {activities.map((activity) => (
                  <option key={activity.id} value={activity.id}>
                    {activity.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Confidentiality</span>
              <select className="field" value={confidentialityLevel} onChange={(event) => setConfidentialityLevel(event.target.value)}>
                {confidentialityOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Source Type</span>
              <input className="field" value={sourceType} onChange={(event) => setSourceType(event.target.value)} />
            </label>
            <label className="space-y-2 text-sm font-semibold md:col-span-2">
              <span>Source Name</span>
              <input className="field" value={sourceName} onChange={(event) => setSourceName(event.target.value)} />
            </label>
            <label className="space-y-2 text-sm font-semibold md:col-span-2 xl:col-span-3">
              <span>Evidence Description</span>
              <RichTextEditor value={evidenceDescription} onChange={setEvidenceDescription} placeholder="Evidence description" minHeightClass="min-h-24" />
            </label>
            <label className="space-y-2 text-sm font-semibold md:col-span-2 xl:col-span-3">
              <span>Evidence File</span>
              <input className="field" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            </label>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              className="button-primary"
              onClick={async () => {
                if (!auditId || !file) return;
                try {
                  const formData = new FormData();
                  formData.append("audit_id", auditId);
                  if (activityId) formData.append("activity_id", activityId);
                  formData.append("source_type", sourceType);
                  formData.append("source_name", sourceName);
                  formData.append("evidence_description", evidenceDescription);
                  formData.append("confidentiality_level", confidentialityLevel);
                  formData.append("file", file);
                  await apiFetch("/evidence", { method: "POST", body: formData });
                  setSourceType("Walkthrough");
                  setSourceName("");
                  setEvidenceDescription("");
                  setActivityId("");
                  setConfidentialityLevel("Internal");
                  setFile(null);
                  setSuccess("Evidence registered.");
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
            <p className="text-sm text-slate">Evidence stays independent from workpapers so the same support can be linked across multiple records.</p>
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
            <Link href={`/evidence/${row.id}`} className="button-secondary px-4 py-2">
              Open
            </Link>
            <button className="button-secondary px-4 py-2" onClick={() => apiOpenFile(`/evidence/${row.id}/view`)}>
              View File
            </button>
            <button className="button-secondary px-4 py-2" onClick={() => apiDownload(`/evidence/${row.id}/download`, `${row.evidence_code}.bin`)}>
              Download
            </button>
          </div>
        )}
      />
    </PageShell>
  );
}
