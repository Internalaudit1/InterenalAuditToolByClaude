import { apiDownload, apiDownloadPost, apiFetch } from "@/lib/api";

export type ImportRowError = {
  row_number: number;
  field?: string | null;
  value?: unknown;
  message: string;
};

export type ImportValidationResponse = {
  resource: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  can_commit: boolean;
  errors: ImportRowError[];
};

export type ImportCommitResponse = {
  resource: string;
  imported_rows: number;
  skipped_rows: number;
  message: string;
  validation: ImportValidationResponse;
};

export const MASTER_IMPORT_RESOURCES = new Set([
  "countries",
  "states",
  "cities",
  "companies",
  "processes",
  "locations",
  "process-location-mappings",
  "risk-types",
  "root-causes",
  "impacts",
  "recommendations",
  "report-considerations",
  "trial-balances",
  "observation-gradings",
  "audit-escalations",
  "designations",
  "control-performance-indicators",
  "task-swaps"
]);

export const PHASE_ONE_MASTER_IMPORT_RESOURCES = MASTER_IMPORT_RESOURCES;

function formDataFor(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return formData;
}

export async function downloadMasterImportTemplate(resource: string) {
  return apiDownload(`/imports/master/${resource}/template`, `${resource}-import-template.xlsx`);
}

export async function validateMasterImport(resource: string, file: File) {
  return apiFetch<ImportValidationResponse>(`/imports/master/${resource}/validate`, {
    method: "POST",
    body: formDataFor(file)
  });
}

export async function commitMasterImport(resource: string, file: File) {
  return apiFetch<ImportCommitResponse>(`/imports/master/${resource}/commit`, {
    method: "POST",
    body: formDataFor(file)
  });
}

export async function downloadMasterImportErrorReport(resource: string, file: File) {
  return apiDownloadPost(`/imports/master/${resource}/error-report`, `${resource}-import-errors.xlsx`, formDataFor(file));
}
