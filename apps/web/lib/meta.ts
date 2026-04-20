import { ColumnDef } from "@tanstack/react-table";

import { formatDate } from "@/lib/utils";

export type MetaForeignKey = {
  references_table: string;
  references_column: string;
};

export type MetaLookup = {
  endpoint: string;
  value_field: string;
  label_field: string;
  display_field: string;
  frontend_mode: string;
};

export type MetaTable = {
  table_name: string;
  display_label: string;
  category: string;
  system_table: boolean;
  has_business_route: boolean;
  frontend_mode: "business_page" | "admin_read_only" | "hidden";
  endpoint?: string | null;
};

export type MetaColumn = {
  name: string;
  ordinal_position: number;
  data_type: string;
  nullable: boolean;
  primary_key: boolean;
  foreign_key?: MetaForeignKey | null;
  default?: string | null;
  suggested_display_label: string;
  editable: boolean;
  system_managed: boolean;
  hidden_by_default: boolean;
  input_type: string;
  lookup?: MetaLookup | null;
};

export type MetaRelationship = {
  direction: string;
  constraint_name?: string | null;
  local_column: string;
  related_table: string;
  related_column: string;
};

export type MetaRowsResponse = {
  items: Record<string, unknown>[];
  meta: {
    page: number;
    page_size: number;
    total: number;
  };
};

const FALLBACK_LABEL_FIELDS = ["name", "title", "full_name", "username", "code", "audit_number", "action_plan_id", "observation_number", "location_code", "id"];

export const DEFAULT_HIDDEN_FIELDS = ["id", "created_at", "updated_at", "created_by", "updated_by", "deleted_at", "is_deleted"];

export function normalizeItems(payload: unknown): Record<string, unknown>[] {
  if (Array.isArray(payload)) {
    return payload as Record<string, unknown>[];
  }
  if (payload && typeof payload === "object" && Array.isArray((payload as { items?: unknown }).items)) {
    return (payload as { items: Record<string, unknown>[] }).items;
  }
  return [];
}

export function labelForLookupRow(row: Record<string, unknown>, preferred?: string) {
  const candidates = preferred ? [preferred, ...FALLBACK_LABEL_FIELDS] : FALLBACK_LABEL_FIELDS;
  const key = candidates.find((candidate) => row[candidate] !== undefined && row[candidate] !== null && row[candidate] !== "");
  return String(key ? row[key] : row.id ?? "");
}

export function accessorKeysFromColumns(columns?: ColumnDef<Record<string, unknown>>[]) {
  return (columns ?? [])
    .map((column) => ("accessorKey" in column && typeof column.accessorKey === "string" ? column.accessorKey : ""))
    .filter(Boolean);
}

function formatCellValue(value: unknown, column: MetaColumn) {
  if (value === null || value === undefined || value === "") return "--";
  if (Array.isArray(value)) return value.map((item) => (typeof item === "object" ? JSON.stringify(item) : String(item))).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (column.input_type === "date" || column.input_type === "datetime") return formatDate(String(value));
  return String(value);
}

export function buildMetadataColumns(
  metaColumns: MetaColumn[],
  options: {
    preferredOrder?: string[];
    hiddenFields?: string[];
  } = {}
): ColumnDef<Record<string, unknown>>[] {
  const hidden = new Set([...DEFAULT_HIDDEN_FIELDS, ...(options.hiddenFields ?? [])]);
  const order = new Map((options.preferredOrder ?? []).map((name, index) => [name, index]));
  const visibleColumns = metaColumns
    .filter((column) => !hidden.has(column.name) && !column.hidden_by_default)
    .sort((left, right) => {
      const leftRank = order.has(left.name) ? order.get(left.name)! : Number.MAX_SAFE_INTEGER;
      const rightRank = order.has(right.name) ? order.get(right.name)! : Number.MAX_SAFE_INTEGER;
      if (leftRank !== rightRank) return leftRank - rightRank;
      return left.ordinal_position - right.ordinal_position;
    });

  return visibleColumns.map((column) => ({
    accessorKey: column.name,
    header: column.suggested_display_label,
    cell: ({ row }) => {
      const displayValue = column.lookup?.display_field ? row.original[column.lookup.display_field] : undefined;
      return formatCellValue(displayValue ?? row.original[column.name], column);
    }
  }));
}

export function toFieldType(inputType?: string): "text" | "textarea" | "date" | "select" | "checkbox" | "number" {
  if (inputType === "select") return "select";
  if (inputType === "checkbox") return "checkbox";
  if (inputType === "date") return "date";
  if (inputType === "number") return "number";
  if (inputType === "textarea" || inputType === "json") return "textarea";
  return "text";
}

export function coerceFormValue(value: unknown, column?: MetaColumn) {
  if (value === "" || value === undefined) return undefined;
  if (!column) return value;
  if (column.input_type === "number" || column.lookup) {
    const numeric = Number(value);
    return Number.isNaN(numeric) ? value : numeric;
  }
  if (column.input_type === "checkbox") {
    return Boolean(value);
  }
  return value;
}
