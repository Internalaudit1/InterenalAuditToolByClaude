"use client";

import { useState } from "react";

import {
  commitMasterImport,
  downloadMasterImportErrorReport,
  downloadMasterImportTemplate,
  ImportValidationResponse,
  validateMasterImport
} from "@/lib/imports";

type Props = {
  resource: string;
  onImported: () => Promise<void> | void;
};

export function MasterImportPanel({ resource, onImported }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<ImportValidationResponse | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busyAction, setBusyAction] = useState<string | null>(null);

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
    <section className="panel p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate">Excel Import</p>
          <h2 className="mt-1 font-serif text-2xl">Bulk Import Master Data</h2>
          <p className="mt-2 max-w-3xl text-sm text-slate">
            Uses strict insert-only import. Validate the workbook first; import is enabled only when every row passes validation.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="button-secondary"
            disabled={busyAction !== null}
            onClick={() => runAction("template", () => downloadMasterImportTemplate(resource))}
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
                    const result = await validateMasterImport(resource, file);
                    setValidation(result);
                    setSuccess(result.can_commit ? "Validation passed. The file is ready to import." : "Validation completed with errors.");
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
                ? runAction("import", async () => {
                    const result = await commitMasterImport(resource, file);
                    setSuccess(result.message);
                    setValidation(result.validation);
                    await onImported();
                  })
                : undefined
            }
          >
            Import
          </button>
          <button
            type="button"
            className="button-danger"
            disabled={!file || !validation?.errors.length || busyAction !== null}
            onClick={() => (file ? runAction("error-report", () => downloadMasterImportErrorReport(resource, file)) : undefined)}
          >
            Download Error Report
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate">
        <span>Selected file: {file ? file.name : "None"}</span>
        {busyAction ? <span>Working on {busyAction}...</span> : null}
      </div>

      {validation ? (
        <div className="mt-5 grid gap-3 md:grid-cols-4">
          <div className="rounded-2xl bg-sand/60 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-slate">Total Rows</p>
            <p className="mt-2 text-2xl font-semibold">{validation.total_rows}</p>
          </div>
          <div className="rounded-2xl bg-emerald-100 p-4 text-emerald-900">
            <p className="text-xs uppercase tracking-[0.16em]">Valid Rows</p>
            <p className="mt-2 text-2xl font-semibold">{validation.valid_rows}</p>
          </div>
          <div className="rounded-2xl bg-ember/10 p-4 text-ember">
            <p className="text-xs uppercase tracking-[0.16em]">Invalid Rows</p>
            <p className="mt-2 text-2xl font-semibold">{validation.invalid_rows}</p>
          </div>
          <div className="rounded-2xl bg-sand/60 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-slate">Commit Status</p>
            <p className="mt-2 text-sm font-semibold">{validation.can_commit ? "Ready to import" : "Fix errors first"}</p>
          </div>
        </div>
      ) : null}

      {validation?.errors.length ? (
        <div className="mt-5 overflow-x-auto rounded-2xl border border-sand/70">
          <table className="min-w-full text-sm">
            <thead className="bg-sand/60 text-left text-xs uppercase tracking-[0.16em] text-slate">
              <tr>
                <th className="px-4 py-3">Row</th>
                <th className="px-4 py-3">Field</th>
                <th className="px-4 py-3">Value</th>
                <th className="px-4 py-3">Error</th>
              </tr>
            </thead>
            <tbody>
              {validation.errors.slice(0, 25).map((item, index) => (
                <tr key={`${item.row_number}-${item.field}-${index}`} className="border-t border-sand/60 bg-white/70">
                  <td className="px-4 py-3">{item.row_number || "File"}</td>
                  <td className="px-4 py-3">{item.field ?? "Workbook"}</td>
                  <td className="px-4 py-3">{item.value == null ? "-" : String(item.value)}</td>
                  <td className="px-4 py-3 text-ember">{item.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {validation.errors.length > 25 ? <p className="px-4 py-3 text-sm text-slate">Showing first 25 errors. Download the error report for the full list.</p> : null}
        </div>
      ) : null}

      {success ? <div className="mt-4 rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{success}</div> : null}
      {error ? <div className="mt-4 rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
    </section>
  );
}
