"use client";

import { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { StatGrid } from "@/components/stat-grid";
import { DataTable } from "@/components/table/data-table";
import { apiFetch } from "@/lib/api";
import { getPrimaryRole, hasPermission } from "@/lib/auth";
import { richTextToPlainText } from "@/lib/rich-text";

type Summary = { all: number; in_progress: number; pending: number; completed: number; overdue: number; due_soon: number };
type BulkDeleteResponse = { deleted_ids: number[]; blocked: { id: number; reason: string }[]; message: string };

const columns: ColumnDef<Record<string, unknown>>[] = [
  { accessorKey: "action_plan_id", header: "Action Plan" },
  { accessorKey: "audit_number", header: "Audit No" },
  { accessorKey: "observation_heading", header: "Observation" },
  {
    accessorKey: "management_implementation_remarks",
    header: "Auditee Remarks",
    cell: ({ row }) => {
      const value = richTextToPlainText(String(row.original.management_implementation_remarks ?? "")).trim();
      if (!value) {
        return <span className="text-slate">--</span>;
      }
      const displayValue = value.length > 80 ? `${value.slice(0, 80)}...` : value;
      return <span title={value}>{displayValue}</span>;
    }
  },
  { accessorKey: "auditor_status", header: "Auditor Status" },
  { accessorKey: "auditee_status", header: "Auditee Status" },
  { accessorKey: "agreed_timeline", header: "Target Date" }
];

export default function ActionPlansPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [selectedIds, setSelectedIds] = useState<(string | number)[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const role = getPrimaryRole();
  const canCreate = hasPermission("action_plans:create");
  const canDelete = role !== "auditee" && hasPermission("action_plans:delete");

  async function load() {
    try {
      const [summaryData, listData] = await Promise.all([
        apiFetch<Summary>("/action-plans/summary"),
        apiFetch<{ items: Record<string, unknown>[] }>("/action-plans?page_size=50")
      ]);
      setSummary(summaryData);
      setRows(listData.items);
      setSelectedIds([]);
      setError("");
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this action plan?")) {
      return;
    }
    try {
      const response = await apiFetch<{ message: string }>(`/action-plans/${id}`, { method: "DELETE" });
      setSuccess(response.message);
      setError("");
      await load();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  async function handleBulkDelete() {
    if (!selectedIds.length || !window.confirm(`Delete ${selectedIds.length} selected action plan(s)?`)) {
      return;
    }
    try {
      const response = await apiFetch<BulkDeleteResponse>("/action-plans/bulk-delete", {
        method: "POST",
        body: JSON.stringify({ ids: selectedIds.map((value) => Number(value)) })
      });
      setSuccess(response.message);
      setError(response.blocked.length ? response.blocked.map((item) => `#${item.id}: ${item.reason}`).join(" | ") : "");
      await load();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <PageShell
      title="Action Plans"
      eyebrow="Remediation Workflow"
      description="Auditor-created action plans, auditee responses, review cycles, evidence handling, and revision tracking are enforced end to end."
      actions={canCreate ? <Link href="/action-plans/new" className="button-primary">New Action Plan</Link> : undefined}
    >
      {success ? <div className="rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{success}</div> : null}
      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      {summary ? (
        <StatGrid
          items={[
            { label: "All Actions", value: summary.all },
            { label: "In Progress", value: summary.in_progress },
            { label: "Pending", value: summary.pending },
            { label: "Completed", value: summary.completed },
            { label: "Overdue", value: summary.overdue },
            { label: "Due Soon", value: summary.due_soon }
          ]}
        />
      ) : null}
      <DataTable
        columns={columns}
        data={rows}
        enableRowSelection={canDelete}
        selectedRowIds={selectedIds}
        onSelectedRowIdsChange={setSelectedIds}
        getRowId={(row) => String(row.id ?? "")}
        bulkActions={canDelete && selectedIds.length ? (
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-slate">{selectedIds.length} action plan(s) selected.</p>
            <button type="button" className="button-danger" onClick={handleBulkDelete}>
              Delete Selected
            </button>
          </div>
        ) : undefined}
        renderRowActions={(row) => (
          <div className="flex flex-wrap gap-2">
            <Link className="button-secondary px-4 py-2" href={`/action-plans/${String(row.id)}`}>
              {role === "auditee" ? "Add/Edit Remarks" : "Open"}
            </Link>
            {canDelete ? (
              <button type="button" className="button-danger" onClick={() => handleDelete(Number(row.id))}>
                Delete
              </button>
            ) : null}
          </div>
        )}
      />
    </PageShell>
  );
}
