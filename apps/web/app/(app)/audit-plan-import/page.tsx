"use client";

import { useEffect, useMemo, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { apiDownload, apiFetch } from "@/lib/api";

type RowError = { row_number: number; field?: string | null; value?: unknown; message: string };
type ValidationResult = {
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  can_commit: boolean;
  errors: RowError[];
};
type Company = { id: number; name: string };
type Location = { id: number; description?: string; location_code?: string; company_id: number };

const FISCAL_YEARS = Array.from({ length: 12 }, (_, i) => {
  const start = 2024 + i;
  return `${start}-${start + 1}`;
});

export default function AuditPlanImportPage() {
  const [mode, setMode] = useState<"fixed" | "legacy">("fixed");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  const [companies, setCompanies] = useState<Company[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [fiscalYear, setFiscalYear] = useState("2026-2027");

  useEffect(() => {
    Promise.all([
      apiFetch<{ items: Company[] }>("/master/companies?page_size=200").catch(() => ({ items: [] })),
      apiFetch<{ items: Location[] }>("/master/locations?page_size=500").catch(() => ({ items: [] }))
    ]).then(([c, l]) => {
      setCompanies(c.items ?? []);
      setLocations(l.items ?? []);
    });
  }, []);

  const scopedLocations = useMemo(
    () => (companyId ? locations.filter((l) => String(l.company_id) === companyId) : locations),
    [locations, companyId]
  );

  function baseForm(): FormData {
    const fd = new FormData();
    if (file) fd.append("file", file);
    return fd;
  }

  function legacyForm(): FormData {
    const fd = baseForm();
    fd.append("company_id", companyId);
    fd.append("location_id", locationId);
    fd.append("fiscal_year", fiscalYear);
    return fd;
  }

  const paths = mode === "legacy"
    ? { validate: "/imports/audit-plans/legacy/validate", commit: "/imports/audit-plans/legacy/commit" }
    : { validate: "/imports/audit-plans/validate", commit: "/imports/audit-plans/commit" };

  const legacyReady = mode !== "legacy" || Boolean(companyId && locationId && fiscalYear);

  async function run(kind: "validate" | "commit") {
    if (!file) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const body = mode === "legacy" ? legacyForm() : baseForm();
      if (kind === "validate") {
        const res = await apiFetch<ValidationResult>(paths.validate, { method: "POST", body });
        setResult(res);
        if (res.total_rows === 0) setError("No data rows found in the file.");
      } else {
        const res = await apiFetch<{ imported_rows: number; message: string }>(paths.commit, { method: "POST", body });
        setSuccess(res.message);
        setResult(null);
        setFile(null);
      }
    } catch (err) {
      if (kind === "commit") setError((err as Error).message + " — fix the issues and re-validate.");
      else { setResult(null); setError((err as Error).message); }
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell
      title="Import Audit Plan"
      eyebrow="Audit Planning Engine"
      description="Upload the yearly audit plan. Rows are created as Draft; approve them to lock the plan for the year."
      actions={
        mode === "fixed" ? (
          <button className="button-secondary" onClick={() => apiDownload("/imports/audit-plans/template", "annual-audit-plan-template.xlsx")}>
            Download template
          </button>
        ) : null
      }
    >
      {error ? <div className="panel border-l-4 border-rose-500 p-4 text-sm text-rose-600">{error}</div> : null}
      {success ? <div className="panel border-l-4 border-emerald-500 p-4 text-sm text-emerald-600">{success}</div> : null}

      <section className="panel space-y-4 p-5">
        <div className="flex flex-wrap gap-2">
          <button className={mode === "fixed" ? "button-primary" : "button-secondary"} onClick={() => { setMode("fixed"); setResult(null); }}>
            Fixed template
          </button>
          <button className={mode === "legacy" ? "button-primary" : "button-secondary"} onClick={() => { setMode("legacy"); setResult(null); }}>
            Legacy monthly sheet
          </button>
        </div>

        <p className="text-sm text-slate">
          {mode === "fixed"
            ? "Fixed format columns: Audit Area, Audit Name, Company, Location, Fiscal Year (+ optional Criticality, CARO/Non-CARO, Internal/External)."
            : "Legacy format: your existing flat monthly sheet (Audit Area, Audit Name / Unit Name, Period/Qtr, Executor, Mentor, Audit SPOC, dates). Choose the Company, Location and Fiscal Year to apply to every row; team names are stored in remarks for reference, then assigned in Audit Allocation."}
        </p>

        {mode === "legacy" ? (
          <div className="grid gap-4 md:grid-cols-3">
            <label className="space-y-1 text-sm">
              <span className="text-slate">Company</span>
              <select className="input w-full" value={companyId} onChange={(e) => { setCompanyId(e.target.value); setLocationId(""); }}>
                <option value="">Select company…</option>
                {companies.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate">Location</span>
              <select className="input w-full" value={locationId} onChange={(e) => setLocationId(e.target.value)}>
                <option value="">Select location…</option>
                {scopedLocations.map((l) => (<option key={l.id} value={l.id}>{l.description || l.location_code}</option>))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate">Fiscal year</span>
              <select className="input w-full" value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)}>
                {FISCAL_YEARS.map((fy) => (<option key={fy} value={fy}>{fy}</option>))}
              </select>
            </label>
          </div>
        ) : null}

        <input
          type="file"
          accept=".xlsx"
          onChange={(e) => { setFile(e.target.files?.[0] ?? null); setResult(null); setSuccess(""); }}
          className="block text-sm"
        />
        <div className="flex flex-wrap gap-2">
          <button className="button-secondary" disabled={!file || busy || !legacyReady} onClick={() => run("validate")}>Validate</button>
          <button className="button-primary" disabled={!file || busy || !result?.can_commit} onClick={() => run("commit")}>Import (commit)</button>
        </div>

        {result ? (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-4 text-sm">
              <span>Total rows: <strong>{result.total_rows}</strong></span>
              <span className="text-emerald-600">Valid: <strong>{result.valid_rows}</strong></span>
              <span className="text-rose-600">Invalid: <strong>{result.invalid_rows}</strong></span>
              <span>{result.can_commit ? "Ready to import." : "Fix the issues below before importing."}</span>
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
                        <td className="p-2">{e.row_number === 0 ? "—" : e.row_number}</td>
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
