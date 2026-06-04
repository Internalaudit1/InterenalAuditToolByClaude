"use client";

import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useState } from "react";

import { RichTextEditor } from "@/components/forms/rich-text-editor";
import { PageShell } from "@/components/layout/page-shell";
import { DataTable } from "@/components/table/data-table";
import { apiFetch } from "@/lib/api";

const columns: ColumnDef<Record<string, unknown>>[] = [
  { accessorKey: "observation_number", header: "Observation" },
  { accessorKey: "audit_id", header: "Audit" },
  { accessorKey: "heading", header: "Heading" },
  { accessorKey: "status", header: "Status" },
  { accessorKey: "auditee_name", header: "Auditee" },
  { accessorKey: "auditee_remark", header: "Auditee Remark" }
];

export default function ObservationsPage() {
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [respondingObservation, setRespondingObservation] = useState<Record<string, unknown> | null>(null);
  const [auditeeRemark, setAuditeeRemark] = useState("");

  async function load() {
    await apiFetch<{ items: Record<string, unknown>[] }>("/me/observations?page_size=100")
      .then((data) => {
        setItems(data.items);
        setError("");
      })
      .catch((err) => setError((err as Error).message));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <PageShell title="Observations" eyebrow="Findings" description="Draft, issued, responded, accepted, dropped, and converted audit observations visible to your role.">
      {success ? <div className="rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{success}</div> : null}
      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      <DataTable
        columns={columns}
        data={items}
        renderRowActions={(row) => row.status === "Issued" ? (
          <button
            className="button-secondary px-4 py-2"
            onClick={() => {
              setRespondingObservation(row);
              setAuditeeRemark(String(row.auditee_remark ?? ""));
            }}
          >
            Respond
          </button>
        ) : null}
      />
      {respondingObservation ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6">
          <button
            type="button"
            className="absolute inset-0 bg-ink/50"
            aria-label="Close response editor"
            onClick={() => {
              setRespondingObservation(null);
              setAuditeeRemark("");
            }}
          />
          <section className="relative z-10 w-full max-w-3xl rounded-3xl bg-white p-6 shadow-2xl">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="chip">Auditee Response</p>
                <h2 className="mt-3 font-serif text-3xl">{String(respondingObservation.heading ?? "Observation Response")}</h2>
                <p className="mt-2 text-sm text-slate">Capture a detailed response, including lists or tables if needed.</p>
              </div>
              <button
                type="button"
                className="button-secondary"
                onClick={() => {
                  setRespondingObservation(null);
                  setAuditeeRemark("");
                }}
              >
                Close
              </button>
            </div>
            <div className="mt-5 space-y-4">
              <RichTextEditor
                value={auditeeRemark}
                onChange={setAuditeeRemark}
                placeholder="Enter auditee response"
                minHeightClass="min-h-32"
              />
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  className="button-primary"
                  onClick={async () => {
                    try {
                      await apiFetch(`/observations/${respondingObservation.id}/response`, { method: "POST", body: JSON.stringify({ auditee_remark: auditeeRemark }) });
                      setSuccess("Observation response submitted.");
                      setError("");
                      setRespondingObservation(null);
                      setAuditeeRemark("");
                      await load();
                    } catch (err) {
                      setSuccess("");
                      setError((err as Error).message);
                    }
                  }}
                >
                  Submit Response
                </button>
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </PageShell>
  );
}
