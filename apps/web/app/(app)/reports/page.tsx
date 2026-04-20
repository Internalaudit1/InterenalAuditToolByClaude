"use client";

import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { DataTable } from "@/components/table/data-table";
import { apiDownload, apiFetch } from "@/lib/api";

type ReportSummary = {
  rows: Record<string, unknown>[];
  totals: Record<string, number>;
};

const columns: ColumnDef<Record<string, unknown>>[] = [
  { accessorKey: "audit", header: "Audit" },
  { accessorKey: "location", header: "Location" },
  { accessorKey: "sector", header: "Sector" },
  { accessorKey: "country", header: "Country" },
  { accessorKey: "quarter", header: "Quarter" },
  { accessorKey: "status", header: "Status" },
  { accessorKey: "criticality", header: "Criticality" }
];

export default function ReportsPage() {
  const [data, setData] = useState<ReportSummary>({ rows: [], totals: {} });

  useEffect(() => {
    apiFetch<ReportSummary>("/reports").then(setData).catch(console.error);
  }, []);

  return (
    <PageShell
      title="Reports"
      eyebrow="Filtered Reporting"
      description="Export audit plan, follow-up, data tracker, and activity views. Assumed design: dashboard visuals and report exports are native to this app rather than delegated to a third-party BI login."
      actions={
        <>
          <button className="button-secondary" onClick={() => apiDownload("/reports/export/excel", "dia-report.xlsx")}>
            Export Excel
          </button>
          <button className="button-primary" onClick={() => apiDownload("/reports/export/pdf", "dia-report.pdf")}>
            Export PDF
          </button>
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-4">
        {Object.entries(data.totals).map(([label, value]) => (
          <div key={label} className="panel p-5">
            <p className="text-xs uppercase tracking-[0.16em] text-slate">{label}</p>
            <p className="mt-3 text-4xl font-semibold">{value}</p>
          </div>
        ))}
      </div>
      <DataTable columns={columns} data={data.rows} />
    </PageShell>
  );
}
