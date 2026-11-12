"use client";

import { useMemo, useState } from "react";

import {
  AuditUniverseCandidate,
  AuditUniverseValidationResponse,
  commitAuditUniverseImport,
  downloadAuditUniverseErrorReport,
  downloadAuditUniverseTemplate,
  validateAuditUniverseImport
} from "@/lib/imports";

const summaryCards = [
  ["companies", "Companies"],
  ["locations", "Locations"],
  ["processes", "Processes"],
  ["mappings", "Process Location Mappings"]
];

function formDataLabel(candidate: AuditUniverseCandidate) {
  if (candidate.kind === "process_location_mapping") {
    return `${candidate.company_name ?? "-"} / ${candidate.location_name ?? "-"} / ${candidate.process_name ?? "-"}`;
  }
  if (candidate.kind === "location") {
    return `${candidate.company_name ?? "-"} / ${candidate.name}`;
  }
  return candidate.name;
}

function actionClass(action: string) {
  return action === "existing" ? "bg-sand text-ink" : "bg-emerald-100 text-emerald-900";
}

export default function AuditUniverseSetupPage() {
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<AuditUniverseValidationResponse | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const candidatesByKind = useMemo(() => {
    const grouped: Record<string, AuditUniverseCandidate[]> = {
      company: [],
      location: [],
      process: [],
      process_location_mapping: []
    };
    for (const candidate of validation?.candidates ?? []) {
      grouped[candidate.kind] = [...(grouped[candidate.kind] ?? []), candidate];
    }
    return grouped;
  }, [validation]);

  async function runAction(action: string, callback: () => Promise<void>) {
    try {
      setBusyAction(action);
      setError("");
      await callback();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="page-shell">
        <div>
          <p className="eyebrow">Master Data</p>
          <h1 className="font-serif text-4xl">Audit Universe Setup</h1>
          <p className="mt-2 max-w-4xl text-sm text-slate">
            Upload the approved annual audit plan workbook to create reusable companies, auditable locations, processes, and process-location
            mappings. This prepares the master universe only; it does not create Audit Plans.
          </p>
        </div>
      </section>

      <section className="panel p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate">Annual Plan Workbook</p>
            <h2 className="mt-1 font-serif text-2xl">Build Reusable Master Data</h2>
            <p className="mt-2 max-w-3xl text-sm text-slate">
              Expected headers include <strong>Audit Area</strong> and <strong>Audit Name / Unit Name</strong>. The tool maps Audit Area to
              Process and Unit Name to Company + Location.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="button-secondary"
              disabled={busyAction !== null}
              onClick={() => runAction("template", () => downloadAuditUniverseTemplate())}
            >
              Download Template
            </button>
            <label className="button-secondary cursor-pointer">
              Upload File
              <input
                type="file"
                accept=".xlsx"
                className="hidden"
                onChange={(event) => {
                  const selectedFile = event.target.files?.[0] ?? null;
                  setFile(selectedFile);
                  setValidation(null);
                  setSuccess("");
                  setError("");
                }}
              />
            </label>
            <button
              type="button"
              className="button-secondary"
              disabled={!file || busyAction !== null}
              onClick={() =>
                file
                  ? runAction("validate", async () => {
                      const result = await validateAuditUniverseImport(file);
                      setValidation(result);
                      setSuccess(result.can_commit ? "Validation completed. Usable rows can be committed to master data." : "Validation found no usable rows.");
                    })
                  : undefined
              }
            >
              Validate
            </button>
            <button
              type="button"
              className="button-primary"
              disabled={!file || !validation?.can_commit || busyAction !== null}
              onClick={() =>
                file
                  ? runAction("commit", async () => {
                      const result = await commitAuditUniverseImport(file);
                      setValidation(result.validation);
                      setSuccess(result.message);
                    })
                  : undefined
              }
            >
              Create / Reuse Masters
            </button>
            <button
              type="button"
              className="button-danger"
              disabled={!file || !validation?.unresolved.length || busyAction !== null}
              onClick={() => (file ? runAction("error-report", () => downloadAuditUniverseErrorReport(file)) : undefined)}
            >
              Download Issue Report
            </button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-3 text-sm text-slate">
          <span>Selected file: {file ? file.name : "None"}</span>
          {busyAction ? <span>Working on {busyAction}...</span> : null}
        </div>
        {success ? <div className="mt-4 rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{success}</div> : null}
        {error ? <div className="mt-4 rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      </section>

      {validation ? (
        <>
          <section className="grid gap-3 md:grid-cols-4">
            <div className="rounded-3xl bg-white/80 p-5 shadow-soft">
              <p className="text-xs uppercase tracking-[0.16em] text-slate">Workbook Rows</p>
              <p className="mt-2 text-3xl font-semibold">{validation.total_rows}</p>
            </div>
            <div className="rounded-3xl bg-emerald-100 p-5 text-emerald-900 shadow-soft">
              <p className="text-xs uppercase tracking-[0.16em]">Usable Rows</p>
              <p className="mt-2 text-3xl font-semibold">{validation.usable_rows}</p>
            </div>
            <div className="rounded-3xl bg-ember/10 p-5 text-ember shadow-soft">
              <p className="text-xs uppercase tracking-[0.16em]">Needs Review</p>
              <p className="mt-2 text-3xl font-semibold">{validation.unresolved_rows}</p>
            </div>
            <div className="rounded-3xl bg-white/80 p-5 shadow-soft">
              <p className="text-xs uppercase tracking-[0.16em] text-slate">Commit Status</p>
              <p className="mt-2 text-sm font-semibold">{validation.can_commit ? "Ready for master setup" : "No commit available"}</p>
            </div>
          </section>

          <section className="panel p-6">
            <h2 className="font-serif text-2xl">Master Data Impact</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-4">
              {summaryCards.map(([key, label]) => (
                <div key={key} className="rounded-2xl bg-sand/60 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate">{label}</p>
                  <p className="mt-2 text-sm">
                    Create <strong>{validation.summary[`${key}_create`] ?? 0}</strong> / Existing{" "}
                    <strong>{validation.summary[`${key}_existing`] ?? 0}</strong>
                  </p>
                </div>
              ))}
            </div>
            {validation.warnings.length ? (
              <div className="mt-4 space-y-2">
                {validation.warnings.map((warning) => (
                  <p key={warning} className="rounded-2xl bg-gold/10 px-4 py-3 text-sm text-slate">
                    {warning}
                  </p>
                ))}
              </div>
            ) : null}
          </section>

          <section className="panel p-6">
            <h2 className="font-serif text-2xl">Candidate Masters</h2>
            <div className="mt-4 grid gap-5 xl:grid-cols-2">
              {[
                ["company", "Companies"],
                ["location", "Locations / Auditable Units"],
                ["process", "Processes / Audit Areas"],
                ["process_location_mapping", "Process Location Mappings"]
              ].map(([kind, label]) => (
                <div key={kind} className="overflow-hidden rounded-2xl border border-sand/70">
                  <div className="bg-sand/60 px-4 py-3">
                    <h3 className="font-semibold">{label}</h3>
                  </div>
                  <div className="max-h-[360px] overflow-auto">
                    <table className="min-w-full text-sm">
                      <thead className="sticky top-0 bg-white text-left text-xs uppercase tracking-[0.16em] text-slate">
                        <tr>
                          <th className="px-4 py-3">Action</th>
                          <th className="px-4 py-3">Master Value</th>
                          <th className="px-4 py-3">Rows</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(candidatesByKind[kind] ?? []).slice(0, 80).map((candidate) => (
                          <tr key={`${candidate.kind}-${candidate.name}-${candidate.company_name ?? ""}`} className="border-t border-sand/60">
                            <td className="px-4 py-3">
                              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${actionClass(candidate.action)}`}>{candidate.action}</span>
                            </td>
                            <td className="px-4 py-3">{formDataLabel(candidate)}</td>
                            <td className="px-4 py-3">{candidate.row_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {validation.unresolved.length ? (
            <section className="panel p-6">
              <h2 className="font-serif text-2xl">Rows Needing Review</h2>
              <p className="mt-2 text-sm text-slate">
                These rows are not committed as process-location mappings because the unit value could not be safely mapped to Company + Location.
              </p>
              <div className="mt-4 max-h-[360px] overflow-auto rounded-2xl border border-sand/70">
                <table className="min-w-full text-sm">
                  <thead className="sticky top-0 bg-sand/60 text-left text-xs uppercase tracking-[0.16em] text-slate">
                    <tr>
                      <th className="px-4 py-3">Row</th>
                      <th className="px-4 py-3">Field</th>
                      <th className="px-4 py-3">Value</th>
                      <th className="px-4 py-3">Issue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {validation.unresolved.slice(0, 100).map((item, index) => (
                      <tr key={`${item.row_number}-${item.field}-${index}`} className="border-t border-sand/60 bg-white/70">
                        <td className="px-4 py-3">{item.row_number || "File"}</td>
                        <td className="px-4 py-3">{item.field ?? "Workbook"}</td>
                        <td className="px-4 py-3">{item.value == null ? "-" : String(item.value)}</td>
                        <td className="px-4 py-3 text-ember">{item.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
