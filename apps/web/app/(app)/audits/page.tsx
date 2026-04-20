"use client";

import Link from "next/link";
import { ColumnDef } from "@tanstack/react-table";

import { ResourcePage } from "@/components/resource-page";

const columns: ColumnDef<Record<string, unknown>>[] = [
  { accessorKey: "audit_number", header: "Audit No" },
  { accessorKey: "audit_name", header: "Audit Name" },
  { accessorKey: "quarter", header: "Quarter" },
  { accessorKey: "fiscal_year", header: "FY" },
  { accessorKey: "status", header: "Status" },
  {
    accessorKey: "id",
    header: "Action",
    cell: ({ row }) => <Link className="text-ember underline" href={`/audits/${String(row.original.id)}`}>View</Link>
  }
];

export default function AuditsPage() {
  return (
    <ResourcePage
      title="Manage Audits"
      eyebrow="Lifecycle Tracking"
      description="Monitor audits across to-be-initiated, in-progress, completed, overdue, and unplanned states. Each audit includes a history timeline and linked remediation actions."
      endpoint="/audits"
      columns={columns}
      fields={[
        { name: "audit_name", label: "Audit Name" },
        { name: "company_id", label: "Company ID" },
        { name: "location_id", label: "Location ID" },
        { name: "quarter", label: "Quarter" },
        { name: "fiscal_year", label: "Fiscal Year" },
        { name: "start_date", label: "Start Date", type: "date" },
        { name: "end_date", label: "End Date", type: "date" },
        { name: "status", label: "Status" },
        { name: "planned_flag", label: "Planned", type: "checkbox" },
        { name: "criticality", label: "Criticality" },
        { name: "audit_owner_id", label: "Audit Owner ID" },
        { name: "remarks", label: "Remarks", type: "textarea" }
      ]}
      editPermission="audits:manage"
      deletePermission="audits:delete"
    />
  );
}
