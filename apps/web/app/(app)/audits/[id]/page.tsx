"use client";

import { ColumnDef } from "@tanstack/react-table";
import { use, useEffect, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { DataTable } from "@/components/table/data-table";
import { apiFetch } from "@/lib/api";

const actionColumns: ColumnDef<Record<string, unknown>>[] = [
  { accessorKey: "action_plan_id", header: "Action Plan" },
  { accessorKey: "observation_heading", header: "Observation" },
  { accessorKey: "auditor_status", header: "Auditor Status" },
  { accessorKey: "auditee_status", header: "Auditee Status" }
];

export default function AuditDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [audit, setAudit] = useState<any>(null);
  const [actions, setActions] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    Promise.all([apiFetch<any>(`/audits/${id}`), apiFetch<{ items: Record<string, unknown>[] }>(`/action-plans?audit_id=${id}`)])
      .then(([auditData, actionData]) => {
        setAudit(auditData);
        setActions(actionData.items);
      })
      .catch(console.error);
  }, [id]);

  if (!audit) return null;

  return (
    <PageShell title={audit.audit_name} eyebrow={audit.audit_number} description="Manage audit execution details, lifecycle history, and linked action plans from one place.">
      <section className="panel p-6">
        <div className="grid gap-4 md:grid-cols-3">
          <div><p className="chip">Status</p><p className="mt-3 text-lg font-semibold">{audit.status}</p></div>
          <div><p className="chip">Quarter</p><p className="mt-3 text-lg font-semibold">{audit.quarter}</p></div>
          <div><p className="chip">Criticality</p><p className="mt-3 text-lg font-semibold">{audit.criticality}</p></div>
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
      <section>
        <h2 className="mb-4 font-serif text-2xl">Linked Action Plans</h2>
        <DataTable columns={actionColumns} data={actions} />
      </section>
    </PageShell>
  );
}
