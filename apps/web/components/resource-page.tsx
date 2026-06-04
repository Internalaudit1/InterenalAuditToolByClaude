"use client";

import { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AsyncLookupField } from "@/components/forms/async-lookup";
import { DataTable } from "@/components/table/data-table";
import { RichTextEditor } from "@/components/forms/rich-text-editor";
import { PageShell } from "@/components/layout/page-shell";
import { MasterImportPanel } from "@/components/master-import-panel";
import { apiFetch } from "@/lib/api";
import { getPrimaryRole, hasPermission } from "@/lib/auth";
import { accessorKeysFromColumns, buildMetadataColumns, coerceFormValue, labelForLookupRow, MetaColumn, normalizeItems, toFieldType } from "@/lib/meta";

export type ResourceField = {
  name: string;
  label: string;
  type?: "text" | "textarea" | "date" | "select" | "checkbox" | "number" | "lookup";
  options?: { label: string; value: string | number }[];
  lookup?: {
    endpoint: string;
    queryParam?: string;
    minChars?: number;
    valueField?: string;
    labelField?: string;
    descriptionFields?: string[];
    staticParams?: Record<string, string | number | boolean>;
  };
  displayField?: string;
  dependsOn?: string;
  optionsByParent?: Record<string, { label: string; value: string | number }[]>;
  disabledPlaceholder?: string;
};

type SelectOption = { label: string; value: string | number };

type Props = {
  title: string;
  eyebrow: string;
  description: string;
  endpoint: string;
  tableName?: string;
  fields?: ResourceField[];
  columns?: ColumnDef<Record<string, unknown>>[];
  columnOrder?: string[];
  hiddenFields?: string[];
  createEnabled?: boolean;
  primaryActionHref?: string;
  primaryActionLabel?: string;
  editPermission?: string;
  deletePermission?: string;
  importResource?: string;
};

type BulkDeleteResponse = {
  deleted_ids: number[];
  blocked: { id: number; reason: string }[];
  message: string;
};

export function ResourcePage({
  title,
  eyebrow,
  description,
  endpoint,
  tableName,
  fields = [],
  columns,
  columnOrder,
  hiddenFields,
  createEnabled = false,
  primaryActionHref,
  primaryActionLabel,
  editPermission,
  deletePermission,
  importResource
}: Props) {
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [editForm, setEditForm] = useState<Record<string, unknown>>({});
  const [editingItem, setEditingItem] = useState<Record<string, unknown> | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedIds, setSelectedIds] = useState<(string | number)[]>([]);
  const [metaColumns, setMetaColumns] = useState<MetaColumn[]>([]);
  const [lookupOptions, setLookupOptions] = useState<Record<string, SelectOption[]>>({});
  const [stateOptionsByCountry, setStateOptionsByCountry] = useState<Record<string, SelectOption[]>>({});
  const [cityOptionsByState, setCityOptionsByState] = useState<Record<string, SelectOption[]>>({});
  const role = getPrimaryRole();
  const canEdit = Boolean(editPermission && role !== "auditee" && hasPermission(editPermission));
  const canDelete = Boolean(deletePermission && role !== "auditee" && hasPermission(deletePermission));
  const canImport = Boolean(importResource && role !== "auditee" && hasPermission("masters:manage"));
  const baseEndpoint = endpoint.split("?")[0];
  const metadataByName = Object.fromEntries(metaColumns.map((column) => [column.name, column])) as Record<string, MetaColumn | undefined>;
  const preferredOrder = columnOrder?.length ? columnOrder : accessorKeysFromColumns(columns);
  const tableColumns = metaColumns.length ? buildMetadataColumns(metaColumns, { preferredOrder, hiddenFields }) : columns ?? [];
  const endpointFilters = new URLSearchParams(endpoint.split("?")[1] ?? "");
  const configuredFields: ResourceField[] = fields.length ? fields : metaColumns.filter((column) => column.editable && !column.hidden_by_default).map((column) => ({
    name: column.name,
    label: column.suggested_display_label
  }));
  const formFields = (
    fields.length &&
    metaColumns.some((column) => column.name === "is_active" && column.editable && !column.hidden_by_default) &&
    !configuredFields.some((field) => field.name === "is_active")
  )
    ? [...configuredFields, { name: "is_active", label: "Is Active", type: "checkbox" } satisfies ResourceField]
    : configuredFields;
  const formFieldNames = new Set(formFields.map((field) => field.name));
  const hasCountryStateCascade = formFieldNames.has("country_id") && formFieldNames.has("state_id");
  const hasStateCityCascade = formFieldNames.has("state_id") && formFieldNames.has("city_id");
  const resolvedFields = formFields.map((field) => {
    const column = metadataByName[field.name];
    return {
      ...field,
      label: field.label || column?.suggested_display_label || field.name,
      type: field.type ?? toFieldType(column?.lookup ? "select" : column?.input_type),
      options: field.options ?? lookupOptions[field.name]
    };
  });

  function isDependentGeographyField(fieldName: string) {
    return (fieldName === "state_id" && hasCountryStateCascade) || (fieldName === "city_id" && hasStateCityCascade);
  }

  function buildLookupOptions(payload: unknown, valueField: string, labelField?: string) {
    return normalizeItems(payload)
      .filter((row) => row.is_active !== false)
      .map((row) => ({
        value: row[valueField] as string | number,
        label: labelForLookupRow(row, labelField)
      }))
      .filter((option) => option.value !== undefined && option.value !== null && option.value !== "");
  }

  function applyFieldChange(previous: Record<string, unknown>, fieldName: string, value: unknown) {
    const next = { ...previous, [fieldName]: value };
    formFields.forEach((field) => {
      if (field.dependsOn === fieldName) {
        next[field.name] = "";
      }
    });
    if (fieldName === "country_id" && hasCountryStateCascade) {
      next.state_id = "";
      if (hasStateCityCascade) {
        next.city_id = "";
      }
    }
    if (fieldName === "state_id" && hasStateCityCascade) {
      next.city_id = "";
    }
    return next;
  }

  function validateDateRange(source: Record<string, unknown>) {
    const startDate = String(source.start_date ?? "");
    const endDate = String(source.end_date ?? "");
    if (startDate && endDate && endDate < startDate) {
      return "End Date must be on or after Start Date.";
    }
    return "";
  }

  function validateForm(source: Record<string, unknown>) {
    return validateGeographySelection(source) || validatePeriodSelection(source) || validateFiscalYear(source) || validateDateRange(source);
  }

  function getFieldOptions(field: ResourceField, values: Record<string, unknown>) {
    if (field.dependsOn && field.optionsByParent) {
      const parentValue = String(values[field.dependsOn] ?? "");
      return parentValue ? field.optionsByParent[parentValue] ?? [] : [];
    }
    if (field.name === "state_id" && hasCountryStateCascade) {
      const countryId = String(values.country_id ?? "");
      return countryId ? stateOptionsByCountry[countryId] ?? [] : [];
    }
    if (field.name === "city_id" && hasStateCityCascade) {
      const stateId = String(values.state_id ?? "");
      return stateId ? cityOptionsByState[stateId] ?? [] : [];
    }
    return field.options ?? [];
  }

  function getSelectPlaceholder(field: ResourceField, values: Record<string, unknown>) {
    if (field.dependsOn && !values[field.dependsOn]) {
      return field.disabledPlaceholder ?? `Select ${field.dependsOn} first`;
    }
    if (field.name === "state_id" && hasCountryStateCascade && !values.country_id) {
      return "Select Country first";
    }
    if (field.name === "city_id" && hasStateCityCascade && !values.state_id) {
      return "Select State first";
    }
    return `Select ${field.label}`;
  }

  function isSelectDisabled(field: ResourceField, values: Record<string, unknown>) {
    if (field.dependsOn && !values[field.dependsOn]) {
      return true;
    }
    return (field.name === "state_id" && hasCountryStateCascade && !values.country_id)
      || (field.name === "city_id" && hasStateCityCascade && !values.state_id);
  }

  function validateGeographySelection(source: Record<string, unknown>) {
    if (hasCountryStateCascade && source.country_id && !source.state_id) {
      return "Select a State for the selected Country.";
    }
    if (hasStateCityCascade && source.state_id && !source.city_id) {
      return "Select a City for the selected State.";
    }
    return "";
  }

  function validatePeriodSelection(source: Record<string, unknown>) {
    const periodValueField = formFields.find((field) => field.name === "period_value");
    if (!formFieldNames.has("period_type") && !periodValueField) {
      return "";
    }
    if (!source.period_type) {
      return "Select Period Type.";
    }
    if (!source.period_value) {
      return "Select Period Value.";
    }
    if (periodValueField && !getFieldOptions(periodValueField, source).some((option) => String(option.value) === String(source.period_value))) {
      return "Period Value must match the selected Period Type.";
    }
    return "";
  }

  function validateFiscalYear(source: Record<string, unknown>) {
    if (formFieldNames.has("fiscal_year") && !source.fiscal_year) {
      return "Select Fiscal Year.";
    }
    return "";
  }

  function buildRowsEndpoint() {
    if (!tableName) {
      const joiner = endpoint.includes("?") ? "&" : "?";
      return `${endpoint}${joiner}search=${encodeURIComponent(search)}`;
    }
    const params = new URLSearchParams(endpointFilters);
    params.set("page_size", "100");
    if (search) params.set("search", search);
    return `/meta/tables/${tableName}/rows?${params.toString()}`;
  }

  async function load() {
    try {
      const data = await apiFetch<unknown>(buildRowsEndpoint());
      setItems(normalizeItems(data));
      setSelectedIds([]);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function handleEdit(row: Record<string, unknown>) {
    const nextForm = resolvedFields.reduce<Record<string, unknown>>((payload, field) => {
      payload[field.name] = row[field.name] ?? "";
      if (field.type === "lookup") {
        const displayField = field.displayField ?? `${field.name.replace(/_id$/, "")}_name`;
        payload[`${field.name}__label`] = row[displayField] ?? "";
      }
      return payload;
    }, {});
    setEditingItem(row);
    setEditForm(nextForm);
    setSuccess("");
    setError("");
  }

  async function handleEditSubmit() {
    if (!editingItem?.id) return;
    try {
      const validationError = validateForm(editForm);
      if (validationError) {
        setSuccess("");
        setError(validationError);
        return;
      }
      await apiFetch(`${baseEndpoint}/${Number(editingItem.id)}`, {
        method: "PUT",
        body: JSON.stringify(buildSubmitPayload(editForm))
      });
      setEditingItem(null);
      setEditForm({});
      setSuccess("Record updated successfully.");
      setError("");
      await load();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this record?")) {
      return;
    }
    try {
      const response = await apiFetch<{ message: string }>(`${baseEndpoint}/${id}`, { method: "DELETE" });
      setSuccess(response.message);
      setError("");
      await load();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  async function handleBulkDelete() {
    if (!selectedIds.length || !window.confirm(`Delete ${selectedIds.length} selected record(s)?`)) {
      return;
    }
    try {
      const response = await apiFetch<BulkDeleteResponse>(`${baseEndpoint}/bulk-delete`, {
        method: "POST",
        body: JSON.stringify({ ids: selectedIds.map((value) => Number(value)) })
      });
      setSuccess(response.message);
      setError(response.blocked.length ? response.blocked.map((item) => `#${item.id}: ${item.reason}`).join(" | ") : "");
      setSelectedIds([]);
      await load();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  async function handleAuditPlanWorkflow(row: Record<string, unknown>, action: "submit" | "approve" | "defer" | "cancel" | "initiate") {
    const id = Number(row.id);
    if (!id) return;
    const actionPath = action === "submit"
      ? "submit-for-approval"
      : action === "initiate"
        ? "initiate-audit"
        : action;
    const body = JSON.stringify({});
    try {
      await apiFetch(`/planning/audit-plans/${id}/${actionPath}`, { method: "POST", body });
      setSuccess(action === "initiate" ? "Audit initiated from approved plan." : "Audit plan workflow updated.");
      setError("");
      await load();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  function buildSubmitPayload(source: Record<string, unknown>) {
    return resolvedFields.reduce<Record<string, unknown>>((payload, field) => {
      const column = metadataByName[field.name];
      if (field.type === "lookup" && !column) {
        payload[field.name] = source[field.name] === "" || source[field.name] === undefined ? null : Number(source[field.name]);
        return payload;
      }
      if ((source[field.name] === "" || source[field.name] === undefined) && column?.nullable && column.lookup) {
        payload[field.name] = null;
        return payload;
      }
      const value = coerceFormValue(source[field.name], column);
      if (value !== undefined) {
        payload[field.name] = value;
      }
      return payload;
    }, {});
  }

  useEffect(() => {
    if (!tableName) return;
    apiFetch<MetaColumn[]>(`/meta/tables/${tableName}/columns`)
      .then((columns) => {
        setMetaColumns(columns);
        setError("");
      })
      .catch((err) => setError((err as Error).message));
  }, [tableName]);

  useEffect(() => {
    const lookupFields = metaColumns.filter((column) => column.lookup && resolvedFields.some((field) => field.name === column.name));
    if (!lookupFields.length) return;
    lookupFields.forEach((column) => {
      if (isDependentGeographyField(column.name)) return;
      const lookup = column.lookup!;
      const joiner = lookup.endpoint.includes("?") ? "&" : "?";
      apiFetch<unknown>(`${lookup.endpoint}${joiner}page_size=100`)
        .then((payload) => {
          const options = buildLookupOptions(payload, lookup.value_field, lookup.label_field);
          setLookupOptions((prev) => ({ ...prev, [column.name]: options }));
        })
        .catch(() => undefined);
    });
  }, [metaColumns]);

  useEffect(() => {
    if (!hasCountryStateCascade) return;
    [form.country_id, editForm.country_id].forEach((value) => {
      const countryId = String(value ?? "");
      if (!countryId || stateOptionsByCountry[countryId]) return;
      apiFetch<unknown>(`/meta/tables/states/rows?page_size=100&country_id=${encodeURIComponent(countryId)}`)
        .then((payload) => {
          const options = buildLookupOptions(payload, "id", "name");
          setStateOptionsByCountry((prev) => ({ ...prev, [countryId]: options }));
        })
        .catch(() => undefined);
    });
  }, [hasCountryStateCascade, form.country_id, editForm.country_id, stateOptionsByCountry]);

  useEffect(() => {
    if (!hasStateCityCascade) return;
    [form.state_id, editForm.state_id].forEach((value) => {
      const stateId = String(value ?? "");
      if (!stateId || cityOptionsByState[stateId]) return;
      apiFetch<unknown>(`/meta/tables/cities/rows?page_size=100&state_id=${encodeURIComponent(stateId)}`)
        .then((payload) => {
          const options = buildLookupOptions(payload, "id", "name");
          setCityOptionsByState((prev) => ({ ...prev, [stateId]: options }));
        })
        .catch(() => undefined);
    });
  }, [hasStateCityCascade, form.state_id, editForm.state_id, cityOptionsByState]);

  useEffect(() => {
    load();
  }, [search, endpoint, tableName]);

  function renderField(field: ResourceField, values: Record<string, unknown>, setValues: (updater: (prev: Record<string, unknown>) => Record<string, unknown>) => void) {
    return (
      <label key={field.name} className="space-y-2 text-sm font-semibold">
        <span>{field.label}</span>
        {field.type === "textarea" ? (
          <RichTextEditor
            value={String(values[field.name] ?? "")}
            onChange={(nextValue) => {
              setValues((prev) => ({ ...prev, [field.name]: nextValue }));
            }}
            placeholder={`Enter ${field.label}`}
            minHeightClass="min-h-28"
          />
        ) : field.type === "select" ? (
          <select
            className="field"
            disabled={isSelectDisabled(field, values)}
            value={String(values[field.name] ?? "")}
            onChange={(event) => {
              const value = event.target.value;
              setValues((prev) => applyFieldChange(prev, field.name, value));
            }}
          >
            <option value="">{getSelectPlaceholder(field, values)}</option>
            {getFieldOptions(field, values).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        ) : field.type === "lookup" && field.lookup ? (
          <AsyncLookupField
            value={values[field.name] as string | number | null | undefined}
            selectedLabel={String(values[`${field.name}__label`] ?? "") || undefined}
            endpoint={field.lookup.endpoint}
            queryParam={field.lookup.queryParam}
            minChars={field.lookup.minChars}
            placeholder={`Search ${field.label}`}
            staticParams={field.lookup.staticParams}
            mapOption={(row) => {
              const valueField = field.lookup?.valueField ?? "id";
              const rawValue = row[valueField];
              if (rawValue === undefined || rawValue === null || rawValue === "") return null;
              const primaryLabelField = field.lookup?.labelField;
              const label = String(
                (primaryLabelField ? row[primaryLabelField] : undefined)
                ?? row.full_name
                ?? row.name
                ?? row.title
                ?? row.username
                ?? row.location_label
                ?? row.location_code
                ?? row.auditee_code
                ?? rawValue
              );
              const description = field.lookup?.descriptionFields?.map((key) => row[key]).filter(Boolean).join(" - ") ?? null;
              return { value: rawValue as string | number, label, description };
            }}
            onSelect={(option) => {
              setValues((prev) => {
                const next = applyFieldChange(prev, field.name, option?.value ?? "");
                next[`${field.name}__label`] = option?.label ?? "";
                return next;
              });
            }}
          />
        ) : field.type === "checkbox" ? (
          <span className="flex min-h-[44px] items-center gap-3 rounded-2xl border border-sand bg-white px-4">
            <input
              type="checkbox"
              className="h-5 w-5 rounded border-sand text-ink"
              checked={field.name === "is_active" ? Boolean(values[field.name] ?? true) : Boolean(values[field.name])}
              onChange={(event) => {
                const checked = event.currentTarget.checked;
                setValues((prev) => ({ ...prev, [field.name]: checked }));
              }}
            />
            <span className="text-sm font-medium text-muted">
              {field.name === "is_active" ? "Record is active and available in lookups" : "Enabled"}
            </span>
          </span>
        ) : (
          <input
            type={field.type ?? "text"}
            className="field"
            min={field.name === "end_date" && values.start_date ? String(values.start_date) : undefined}
            value={String(values[field.name] ?? "")}
            onChange={(event) => {
              const value = event.target.value;
              setValues((prev) => ({ ...prev, [field.name]: value }));
            }}
          />
        )}
      </label>
    );
  }

  return (
    <PageShell
      title={title}
      eyebrow={eyebrow}
      description={description}
      actions={
        <>
          <input value={search} onChange={(event) => setSearch(event.target.value)} className="field min-w-60" placeholder="Search records" />
          {primaryActionHref && primaryActionLabel ? (
            <Link href={primaryActionHref} className="button-primary">
              {primaryActionLabel}
            </Link>
          ) : null}
        </>
      }
    >
      {canImport && importResource ? <MasterImportPanel resource={importResource} onImported={load} /> : null}
      {createEnabled && role !== "auditee" ? (
        <section className="panel p-4 xl:p-5">
          <h2 className="font-serif text-xl xl:text-2xl">Create Record</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {resolvedFields.map((field) => renderField(field, form, setForm))}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              className="button-primary"
              onClick={async () => {
                try {
                  const validationError = validateForm(form);
                  if (validationError) {
                    setSuccess("");
                    setError(validationError);
                    return;
                  }
                  await apiFetch(endpoint, { method: "POST", body: JSON.stringify(buildSubmitPayload(form)) });
                  setForm({});
                  setSuccess("Record created successfully.");
                  setError("");
                  load();
                } catch (err) {
                  setSuccess("");
                  setError((err as Error).message);
                }
              }}
            >
              Save
            </button>
            <p className="text-sm text-slate">Fill the required fields, then save. Optional dropdowns can be left blank.</p>
          </div>
        </section>
      ) : null}
      {editingItem ? (
        <section className="panel p-4 xl:p-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate">Edit Record</p>
              <h2 className="mt-1 font-serif text-2xl">Update #{String(editingItem.id)}</h2>
            </div>
            <button
              type="button"
              className="button-secondary"
              onClick={() => {
                setEditingItem(null);
                setEditForm({});
              }}
            >
              Cancel
            </button>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {resolvedFields.map((field) => renderField(field, editForm, setEditForm))}
          </div>
          <div className="mt-4 flex items-center gap-3">
            <button type="button" className="button-primary" onClick={handleEditSubmit}>
              Save Changes
            </button>
          </div>
        </section>
      ) : null}
      {success ? <div className="rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{success}</div> : null}
      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      <DataTable
        columns={tableColumns}
        data={items}
        enableRowSelection={canDelete}
        selectedRowIds={selectedIds}
        onSelectedRowIdsChange={setSelectedIds}
        getRowId={(row) => String(row.id ?? "")}
        bulkActions={canDelete && selectedIds.length ? (
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-slate">{selectedIds.length} record(s) selected.</p>
            <button type="button" className="button-danger" onClick={handleBulkDelete}>
              Delete Selected
            </button>
          </div>
        ) : undefined}
        renderRowActions={canEdit || canDelete || tableName === "audit_plans" ? (row) => (
          <div className="flex flex-wrap gap-2">
            {tableName === "audit_plans" && row.approval_status === "Draft" && hasPermission("planning:manage") ? (
              <button type="button" className="button-secondary px-4 py-2" onClick={() => handleAuditPlanWorkflow(row, "submit")}>
                Submit
              </button>
            ) : null}
            {tableName === "audit_plans" && row.approval_status === "Under Review" && hasPermission("planning:approve") ? (
              <>
                <button type="button" className="button-secondary px-4 py-2" onClick={() => handleAuditPlanWorkflow(row, "approve")}>
                  Approve
                </button>
                <button type="button" className="button-secondary px-4 py-2" onClick={() => handleAuditPlanWorkflow(row, "defer")}>
                  Defer
                </button>
                <button type="button" className="button-danger" onClick={() => handleAuditPlanWorkflow(row, "cancel")}>
                  Cancel
                </button>
              </>
            ) : null}
            {tableName === "audit_plans" && row.approval_status === "Approved" && hasPermission("planning:approve") ? (
              <button type="button" className="button-secondary px-4 py-2" onClick={() => handleAuditPlanWorkflow(row, "initiate")}>
                Initiate Audit
              </button>
            ) : null}
            {canEdit ? (
              <button type="button" className="button-secondary px-4 py-2" onClick={() => handleEdit(row)}>
                Edit
              </button>
            ) : null}
            {canDelete ? (
              <button type="button" className="button-danger" onClick={() => handleDelete(Number(row.id))}>
                Delete
              </button>
            ) : null}
          </div>
        ) : undefined}
      />
    </PageShell>
  );
}
