"use client";

import { useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { apiDownload, apiDownloadPost, apiFetch } from "@/lib/api";

type RowError = { row_number: number; field?: string | null; value?: unknown; message: string };
type ValidationResult = {
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  can_commit: boolean;
  errors: RowError[];
};

export default function AuditPlanImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  function formData(): FormData {
    const fd = new FormData();
    if (file) fd.append("file", file);
    return fd;
  }

  async function validate() {
    if (!file) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const res = await apiFetch<ValidationResult>("/imports/audit-plans/validate", { method: "POST", body: formData() });
      setResult(res);
      if (res.total_rows === 0) setError("No data rows found in the file.");
    } catch (err) {
      setResult(null);
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    if (!file) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const res = await apiFetch<{ imported_rows: number; message: string }>("/imports/audit-plans/commit", { method: "POST", body: formData() });
      setSuccess(res.message);
      setResult(null);
      setFile(null);
    } catch (err) {
      setError((err as Error).message + " — fix the rows and re-validate.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell
      title="Import Audit Plan"
      eyebrow="Audit Planning Engine"
      description="Upload the fixed-format annual audit plan. Rows are created as Draft; approve them to lock the plan for the year. Required columns: Audit Area, Audit Name, Company, Location, Fiscal Year (plus optional Criticality, CARO/Non-CARO, Internal/External)."
      actions={
        <button className="button-secondary" onClick={() => apiDownload("/imports/audit-plans/template", "annual-audit-plan-template.xlsx")}>
          Download template
        </button>
      }
    >
      {error ? <div className="panel border-l-4 border-rose-500 p-4 text-sm text-rose-600">{error}</div> : null}
      {success ? <div className="panel border-l-4 border-emerald-500 p-4 text-sm text-emerald-600">{success}</div> : null}

      <section className="panel space-y-4 p-5">
        <input
          type="file"
          accept=".xlsx"
          onChange={(e) => { setFile(e.target.files?.[0] ?? null); setResult(null); setSuccess(""); }}
          className="block text-sm"
        />
        <div className="flex flex-wrap gap-2">
          <button className="button-secondary" disabled={!file || busy} onClick={validate}>Validate</button>
          <button className="button-primary" disabled={!file || busy || !result?.can_commit} onClick={commit}>Import (commit)</button>
          {file ? (
            <button className="button-secondary" disabled={busy} onClick={() => apiDownloadPost("/imports/audit-plans/error-report", "audit-plan-errors.xlsx", formData())}>
              Download error report
            </button>
          ) : null}
        </div>

        {result ? (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-4 text-sm">
              <span>Total rows: <strong>{result.total_rows}</strong></span>
              <span className="text-emerald-600">Valid: <strong>{result.valid_rows}</strong></span>
              <span className="text-rose-600">Invalid: <strong>{result.invalid_rows}</strong></span>
              <span>{result.can_commit ? "Ready to import." : "Fix the errors below before importing."}</span>
            </div>
            {result.errors.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-slate">
                      <th className="p-2">Row</th><th className="p-2">Column</th><th className="p-2">Value</th><th className="p-2">Issue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.errors.map((e, i) => (
                      <tr key={i} className="border-b border-slate-100">
                        <td className="p-2">{e.row_number}</td>
                        <td className="p-2">{e.field ?? "--"}</td>
                        <td className="p-2">{e.value == null ? "--" : String(e.value)}</td>
                        <td className="p-2">{e.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>
    </PageShell>
  );
}
