"use client";

import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { DataTable } from "@/components/table/data-table";
import { apiFetch } from "@/lib/api";

const columns: ColumnDef<Record<string, unknown>>[] = [
  { accessorKey: "audit_id", header: "Audit" },
  { accessorKey: "title", header: "Activity" },
  { accessorKey: "assigned_to_user_id", header: "Assigned To" },
  { accessorKey: "due_date", header: "Due Date" },
  { accessorKey: "status", header: "Status" },
  { accessorKey: "remarks", header: "Remarks" }
];

export default function MyActivitiesPage() {
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<{ items: Record<string, unknown>[] }>("/me/activities?page_size=100")
      .then((data) => {
        setItems(data.items);
        setError("");
      })
      .catch((err) => setError((err as Error).message));
  }, []);

  return (
    <PageShell title="My Activities" eyebrow="Audit Execution" description="Assigned audit activity tracker and execution work queue.">
      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      <DataTable columns={columns} data={items} />
    </PageShell>
  );
}
