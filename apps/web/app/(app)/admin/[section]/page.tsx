"use client";

import { ColumnDef } from "@tanstack/react-table";
import { use, useEffect, useMemo, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { DataTable } from "@/components/table/data-table";
import { apiFetch } from "@/lib/api";
import { getSessionUser, hasPermission } from "@/lib/auth";
import { buildMetadataColumns, MetaColumn, MetaRelationship, MetaTable, normalizeItems } from "@/lib/meta";

type UserRow = Record<string, unknown> & { id?: number; role_codes?: string[] };
type RoleRow = {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  is_system: boolean;
  permission_codes: string[];
  user_count: number;
};
type PermissionRow = { id: number; code: string; description?: string | null };
type LookupOption = { id: number; label: string; isActive: boolean };

type UserFormState = {
  username: string;
  email: string;
  full_name: string;
  password: string;
  phone: string;
  designation_id: string;
  company_id: string;
  location_id: string;
  is_active: boolean;
  role_codes: string[];
};

type RoleFormState = {
  code: string;
  name: string;
  description: string;
  permission_codes: string[];
};

const activityColumns: ColumnDef<Record<string, unknown>>[] = [
  { accessorKey: "module", header: "Module" },
  { accessorKey: "entity_type", header: "Entity Type" },
  { accessorKey: "action_type", header: "Action" },
  { accessorKey: "actor_name", header: "Actor" },
  { accessorKey: "correlation_id", header: "Correlation ID" }
];

const baseUserColumns: ColumnDef<UserRow>[] = [
  { accessorKey: "username", header: "Username" },
  { accessorKey: "full_name", header: "Full Name" },
  { accessorKey: "email", header: "Email" },
  {
    accessorKey: "role_codes",
    header: "Roles",
    cell: ({ row }) => (row.original.role_codes ?? []).join(", ")
  }
];

const roleColumns: ColumnDef<RoleRow>[] = [
  { accessorKey: "code", header: "Code" },
  { accessorKey: "name", header: "Role Name" },
  {
    accessorKey: "is_system",
    header: "Type",
    cell: ({ row }) => (row.original.is_system ? "System" : "Custom")
  },
  { accessorKey: "user_count", header: "Users" },
  {
    accessorKey: "permission_codes",
    header: "Permissions",
    cell: ({ row }) => `${row.original.permission_codes.length} permission(s)`
  }
];

const emptyUserForm: UserFormState = {
  username: "",
  email: "",
  full_name: "",
  password: "",
  phone: "",
  designation_id: "",
  company_id: "",
  location_id: "",
  is_active: true,
  role_codes: []
};

const emptyRoleForm: RoleFormState = {
  code: "",
  name: "",
  description: "",
  permission_codes: []
};

function toOptionalNumber(value: string) {
  return value ? Number(value) : undefined;
}

function textValue(row: Record<string, unknown>, key: string) {
  const value = row[key];
  return value === null || value === undefined ? "" : String(value).trim();
}

function createLookupMap(options: LookupOption[]) {
  return new Map(options.map((option) => [option.id, option]));
}

function buildLookupOptions(payload: unknown, buildLabel: (row: Record<string, unknown>) => string) {
  const options: LookupOption[] = [];
  normalizeItems(payload).forEach((row) => {
    const id = Number(row.id);
    if (!Number.isFinite(id)) return;
    options.push({
      id,
      label: buildLabel(row),
      isActive: row.is_active !== false
    });
  });
  return options.sort((left, right) => left.label.localeCompare(right.label));
}

function designationLabel(row: Record<string, unknown>) {
  return textValue(row, "title") || textValue(row, "code") || `Designation #${row.id}`;
}

function companyLabel(row: Record<string, unknown>) {
  return textValue(row, "name") || `Company #${row.id}`;
}

function locationLabel(row: Record<string, unknown>) {
  const code = textValue(row, "location_code");
  const description = textValue(row, "description");
  if (code && description) return `${code} - ${description}`;
  return description || code || `Location #${row.id}`;
}

function lookupLabel(lookupMap: Map<number, LookupOption>, value: unknown) {
  if (value === null || value === undefined || value === "") return "--";
  const id = Number(value);
  if (!Number.isFinite(id)) return "--";
  const option = lookupMap.get(id);
  if (!option) return `Unmapped #${id}`;
  return option.isActive ? option.label : `${option.label} (Inactive)`;
}

function lookupWarning(label: string, value: string, options: LookupOption[]) {
  if (!value) return "";
  const id = Number(value);
  if (!Number.isFinite(id)) return `${label} selection is invalid.`;
  const option = options.find((item) => item.id === id);
  if (!option) return `${label} #${id} is missing or unavailable. Choose a valid active ${label.toLowerCase()}.`;
  if (!option.isActive) return `${label} "${option.label}" is inactive. Choose an active ${label.toLowerCase()}.`;
  return "";
}

function groupPermissions(permissions: PermissionRow[]) {
  return permissions.reduce<Record<string, PermissionRow[]>>((groups, permission) => {
    const [group] = permission.code.split(":");
    groups[group] = [...(groups[group] ?? []), permission];
    return groups;
  }, {});
}

function toggleValue(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

export default function AdminSectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = use(params);
  const sessionUser = getSessionUser();
  const isSuperAdmin = sessionUser?.roles.includes("super_admin") ?? false;
  const isUsers = section === "users";
  const isRoles = section === "roles";
  const isDataExplorer = section === "data-explorer";

  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [selectedIds, setSelectedIds] = useState<(string | number)[]>([]);
  const [tables, setTables] = useState<MetaTable[]>([]);
  const [selectedTable, setSelectedTable] = useState("");
  const [metaColumns, setMetaColumns] = useState<MetaColumn[]>([]);
  const [relationships, setRelationships] = useState<MetaRelationship[]>([]);
  const [roles, setRoles] = useState<RoleRow[]>([]);
  const [permissions, setPermissions] = useState<PermissionRow[]>([]);
  const [designationOptions, setDesignationOptions] = useState<LookupOption[]>([]);
  const [companyOptions, setCompanyOptions] = useState<LookupOption[]>([]);
  const [locationOptions, setLocationOptions] = useState<LookupOption[]>([]);
  const [creatingUser, setCreatingUser] = useState(false);
  const [editingUser, setEditingUser] = useState<UserRow | null>(null);
  const [userForm, setUserForm] = useState<UserFormState>(emptyUserForm);
  const [creatingRole, setCreatingRole] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleRow | null>(null);
  const [roleForm, setRoleForm] = useState<RoleFormState>(emptyRoleForm);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const canManageUsers = isUsers && hasPermission("users:manage");
  const canDeleteUsers = isUsers && hasPermission("users:delete");
  const canManageRoles = isRoles && hasPermission("roles:manage");
  const assignableRoles = useMemo(() => roles.filter((role) => isSuperAdmin || role.code !== "super_admin"), [roles, isSuperAdmin]);
  const groupedPermissions = useMemo(() => groupPermissions(permissions), [permissions]);
  const designationLookupMap = useMemo(() => createLookupMap(designationOptions), [designationOptions]);
  const companyLookupMap = useMemo(() => createLookupMap(companyOptions), [companyOptions]);
  const locationLookupMap = useMemo(() => createLookupMap(locationOptions), [locationOptions]);
  const userLookupWarnings = useMemo(() => ({
    designation_id: lookupWarning("Designation", userForm.designation_id, designationOptions),
    company_id: lookupWarning("Company", userForm.company_id, companyOptions),
    location_id: lookupWarning("Location", userForm.location_id, locationOptions)
  }), [userForm.designation_id, userForm.company_id, userForm.location_id, designationOptions, companyOptions, locationOptions]);
  const userColumns = useMemo<ColumnDef<UserRow>[]>(() => [
    ...baseUserColumns,
    {
      accessorKey: "designation_id",
      header: "Designation",
      cell: ({ row }) => lookupLabel(designationLookupMap, row.original.designation_id)
    },
    {
      accessorKey: "company_id",
      header: "Company",
      cell: ({ row }) => lookupLabel(companyLookupMap, row.original.company_id)
    },
    {
      accessorKey: "location_id",
      header: "Location",
      cell: ({ row }) => lookupLabel(locationLookupMap, row.original.location_id)
    }
  ], [designationLookupMap, companyLookupMap, locationLookupMap]);

  async function loadRoles() {
    const roleData = await apiFetch<RoleRow[]>("/admin/roles");
    setRoles(roleData);
    return roleData;
  }

  async function loadPermissions() {
    const permissionData = await apiFetch<PermissionRow[]>("/admin/permissions");
    setPermissions(permissionData);
    return permissionData;
  }

  async function loadUserLookups() {
    const [designationData, companyData, locationData] = await Promise.all([
      apiFetch<unknown>("/master/designations?page_size=100"),
      apiFetch<unknown>("/master/companies?page_size=100"),
      apiFetch<unknown>("/master/locations?page_size=100")
    ]);
    setDesignationOptions(buildLookupOptions(designationData, designationLabel));
    setCompanyOptions(buildLookupOptions(companyData, companyLabel));
    setLocationOptions(buildLookupOptions(locationData, locationLabel));
  }

  async function load() {
    try {
      if (isUsers) {
        const [userData] = await Promise.all([apiFetch<UserRow[]>("/admin/users"), loadRoles(), loadUserLookups()]);
        setRows(userData);
      } else if (isRoles) {
        const [roleData] = await Promise.all([loadRoles(), loadPermissions()]);
        setRows(roleData as unknown as Record<string, unknown>[]);
      } else {
        const data = await apiFetch<any>("/admin/activity-logs");
        setRows(data.items ?? data);
      }
      setSelectedIds([]);
      setError("");
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  async function loadExplorerTables() {
    try {
      const data = await apiFetch<MetaTable[]>("/meta/tables");
      const explorerTables = data.filter((table) => table.frontend_mode === "admin_read_only" || table.system_table);
      setTables(explorerTables);
      if (!selectedTable && explorerTables.length) {
        setSelectedTable(explorerTables[0].table_name);
      }
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function loadExplorerRows(tableName: string) {
    if (!tableName) return;
    try {
      const [columns, relationData, rowData] = await Promise.all([
        apiFetch<MetaColumn[]>(`/meta/tables/${tableName}/columns`),
        apiFetch<MetaRelationship[]>(`/meta/tables/${tableName}/relationships`),
        apiFetch<unknown>(`/meta/tables/${tableName}/rows?page_size=100`)
      ]);
      setMetaColumns(columns);
      setRelationships(relationData);
      setRows(normalizeItems(rowData));
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function beginCreateUser() {
    setCreatingUser(true);
    setEditingUser(null);
    setUserForm(emptyUserForm);
    setSuccess("");
    setError("");
  }

  function handleEditUser(row: UserRow) {
    setCreatingUser(false);
    setEditingUser(row);
    setUserForm({
      username: String(row.username ?? ""),
      email: String(row.email ?? ""),
      full_name: String(row.full_name ?? ""),
      password: "",
      phone: String(row.phone ?? ""),
      designation_id: row.designation_id ? String(row.designation_id) : "",
      company_id: row.company_id ? String(row.company_id) : "",
      location_id: row.location_id ? String(row.location_id) : "",
      is_active: Boolean(row.is_active),
      role_codes: row.role_codes ?? []
    });
    setSuccess("");
    setError("");
  }

  async function handleUserSubmit() {
    try {
      const lookupIssues = Object.values(userLookupWarnings).filter(Boolean);
      if (lookupIssues.length) {
        setSuccess("");
        setError(lookupIssues.join(" "));
        return;
      }

      const basePayload = {
        email: userForm.email,
        full_name: userForm.full_name,
        phone: userForm.phone || undefined,
        designation_id: toOptionalNumber(userForm.designation_id),
        company_id: toOptionalNumber(userForm.company_id),
        location_id: toOptionalNumber(userForm.location_id),
        is_active: userForm.is_active
      };

      if (creatingUser) {
        await apiFetch("/admin/users", {
          method: "POST",
          body: JSON.stringify({
            ...basePayload,
            username: userForm.username,
            password: userForm.password,
            role_codes: userForm.role_codes
          })
        });
        setSuccess("User created successfully.");
      } else if (editingUser?.id) {
        await apiFetch(`/admin/users/${Number(editingUser.id)}`, { method: "PUT", body: JSON.stringify(basePayload) });
        await apiFetch(`/admin/users/${Number(editingUser.id)}/roles`, {
          method: "PUT",
          body: JSON.stringify({ role_codes: userForm.role_codes })
        });
        setSuccess("User updated successfully.");
      }

      setCreatingUser(false);
      setEditingUser(null);
      setUserForm(emptyUserForm);
      setError("");
      await load();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  function renderUserLookupField(name: "designation_id" | "company_id" | "location_id", label: string, options: LookupOption[]) {
    const value = userForm[name];
    const currentOption = value ? options.find((option) => String(option.id) === value) : undefined;
    const showCurrentUnavailable = Boolean(value && (!currentOption || !currentOption.isActive));
    const warning = userLookupWarnings[name];
    return (
      <label key={name} className="space-y-2 text-sm font-semibold">
        <span>{label}</span>
        <select
          className="field"
          value={value}
          onChange={(event) => {
            const nextValue = event.target.value;
            setUserForm((prev) => ({ ...prev, [name]: nextValue }));
          }}
        >
          <option value="">Select {label}</option>
          {showCurrentUnavailable ? (
            <option value={value} disabled>
              {currentOption ? `${currentOption.label} (Inactive)` : `Unavailable record #${value}`}
            </option>
          ) : null}
          {options.filter((option) => option.isActive).map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
        {warning ? <p className="text-xs font-medium text-ember">{warning}</p> : null}
      </label>
    );
  }

  async function handleDeleteUser(id: number) {
    if (!window.confirm("Delete this user?")) {
      return;
    }
    try {
      const response = await apiFetch<{ message: string }>(`/admin/users/${id}`, { method: "DELETE" });
      setSuccess(response.message);
      setError("");
      await load();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  async function handleBulkDeleteUsers() {
    if (!selectedIds.length || !window.confirm(`Delete ${selectedIds.length} selected user(s)?`)) {
      return;
    }
    try {
      const response = await apiFetch<{ blocked: { id: number; reason: string }[]; message: string }>("/admin/users/bulk-delete", {
        method: "POST",
        body: JSON.stringify({ ids: selectedIds.map((value) => Number(value)) })
      });
      setSuccess(response.message);
      setError(response.blocked.length ? response.blocked.map((item) => `#${item.id}: ${item.reason}`).join(" | ") : "");
      await load();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  function beginCreateRole() {
    setCreatingRole(true);
    setEditingRole(null);
    setRoleForm(emptyRoleForm);
    setSuccess("");
    setError("");
  }

  function handleEditRole(role: RoleRow) {
    setCreatingRole(false);
    setEditingRole(role);
    setRoleForm({
      code: role.code,
      name: role.name,
      description: role.description ?? "",
      permission_codes: role.permission_codes
    });
    setSuccess("");
    setError("");
  }

  async function handleRoleSubmit() {
    try {
      if (creatingRole) {
        await apiFetch("/admin/roles", { method: "POST", body: JSON.stringify(roleForm) });
        setSuccess("Role created successfully.");
      } else if (editingRole) {
        await apiFetch(`/admin/roles/${editingRole.id}`, {
          method: "PUT",
          body: JSON.stringify({ name: roleForm.name, description: roleForm.description || undefined })
        });
        if (editingRole.code !== "super_admin") {
          await apiFetch(`/admin/roles/${editingRole.id}/permissions`, {
            method: "PUT",
            body: JSON.stringify({ permission_codes: roleForm.permission_codes })
          });
        }
        setSuccess("Role updated successfully.");
      }
      setCreatingRole(false);
      setEditingRole(null);
      setRoleForm(emptyRoleForm);
      setError("");
      await load();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  async function handleDeleteRole(role: RoleRow) {
    if (!window.confirm(`Delete role ${role.name}?`)) {
      return;
    }
    try {
      const response = await apiFetch<{ message: string }>(`/admin/roles/${role.id}`, { method: "DELETE" });
      setSuccess(response.message);
      setError("");
      await load();
    } catch (err) {
      setSuccess("");
      setError((err as Error).message);
    }
  }

  useEffect(() => {
    if (isDataExplorer) {
      loadExplorerTables();
      return;
    }
    load();
  }, [section]);

  useEffect(() => {
    if (isDataExplorer) {
      loadExplorerRows(selectedTable);
    }
  }, [isDataExplorer, selectedTable]);

  if (isDataExplorer) {
    const table = tables.find((item) => item.table_name === selectedTable);
    return (
      <PageShell
        title="Data Explorer"
        eyebrow="Admin"
        description="Read-only metadata view of internal and system-backed tables from the live PostgreSQL database."
        actions={
          <select className="field min-w-72" value={selectedTable} onChange={(event) => setSelectedTable(event.target.value)}>
            {tables.map((item) => (
              <option key={item.table_name} value={item.table_name}>
                {item.display_label}
              </option>
            ))}
          </select>
        }
      >
        {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
        {table ? (
          <section className="panel p-5">
            <div className="grid gap-3 text-sm md:grid-cols-3">
              <p><span className="font-semibold">Table:</span> {table.table_name}</p>
              <p><span className="font-semibold">Category:</span> {table.category}</p>
              <p><span className="font-semibold">Mode:</span> {table.frontend_mode.replace("_", " ")}</p>
            </div>
            {relationships.length ? (
              <div className="mt-4 rounded-2xl bg-sand/50 p-4 text-sm text-slate">
                {relationships.slice(0, 8).map((relationship) => (
                  <p key={`${relationship.direction}-${relationship.related_table}-${relationship.local_column}`}>
                    {relationship.direction}: {relationship.local_column} {"->"} {relationship.related_table}.{relationship.related_column}
                  </p>
                ))}
              </div>
            ) : null}
          </section>
        ) : null}
        <DataTable columns={buildMetadataColumns(metaColumns)} data={rows} />
      </PageShell>
    );
  }

  if (isRoles) {
    return (
      <PageShell
        title="Role Administration"
        eyebrow="Admin"
        description="Create custom roles, tune permission sets, and keep protected system roles audit-safe."
        actions={canManageRoles ? <button type="button" className="button-primary" onClick={beginCreateRole}>New Role</button> : undefined}
      >
        {success ? <div className="rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{success}</div> : null}
        {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
        {creatingRole || editingRole ? (
          <section className="panel p-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate">{creatingRole ? "Create Role" : "Edit Role"}</p>
                <h2 className="mt-1 font-serif text-2xl">{creatingRole ? "New Custom Role" : roleForm.name}</h2>
              </div>
              <button
                type="button"
                className="button-secondary"
                onClick={() => {
                  setCreatingRole(false);
                  setEditingRole(null);
                  setRoleForm(emptyRoleForm);
                }}
              >
                Cancel
              </button>
            </div>
            <div className="mt-5 grid gap-4 md:grid-cols-3">
              <label className="space-y-2 text-sm font-semibold">
                <span>Role Code</span>
                <input
                  className="field"
                  value={roleForm.code}
                  disabled={!creatingRole}
                  placeholder="custom_reviewer"
                  onChange={(event) => setRoleForm((prev) => ({ ...prev, code: event.target.value }))}
                />
              </label>
              <label className="space-y-2 text-sm font-semibold">
                <span>Role Name</span>
                <input className="field" value={roleForm.name} onChange={(event) => setRoleForm((prev) => ({ ...prev, name: event.target.value }))} />
              </label>
              <label className="space-y-2 text-sm font-semibold">
                <span>Description</span>
                <input className="field" value={roleForm.description} onChange={(event) => setRoleForm((prev) => ({ ...prev, description: event.target.value }))} />
              </label>
            </div>
            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              {Object.entries(groupedPermissions).map(([group, items]) => (
                <fieldset key={group} className="rounded-2xl border border-sand bg-cream p-4">
                  <legend className="px-2 text-sm font-semibold capitalize">{group.replace("_", " ")}</legend>
                  <div className="mt-3 grid gap-2">
                    {items.map((permission) => {
                      const disabled = permission.code.startsWith("roles:") || editingRole?.code === "super_admin";
                      return (
                        <label key={permission.code} className="flex items-center gap-2 text-sm text-slate">
                          <input
                            type="checkbox"
                            disabled={disabled}
                            checked={roleForm.permission_codes.includes(permission.code)}
                            onChange={() => setRoleForm((prev) => ({ ...prev, permission_codes: toggleValue(prev.permission_codes, permission.code) }))}
                          />
                          <span>{permission.code}</span>
                        </label>
                      );
                    })}
                  </div>
                </fieldset>
              ))}
            </div>
            <button type="button" className="button-primary mt-5" onClick={handleRoleSubmit}>
              Save Role
            </button>
          </section>
        ) : null}
        <DataTable
          columns={roleColumns}
          data={roles}
          getRowId={(row) => String(row.id)}
          renderRowActions={canManageRoles ? (role) => (
            <div className="flex flex-wrap gap-2">
              <button type="button" className="button-secondary px-4 py-2" onClick={() => handleEditRole(role)}>
                Edit
              </button>
              <button type="button" className="button-danger" disabled={role.is_system} onClick={() => handleDeleteRole(role)}>
                Delete
              </button>
            </div>
          ) : undefined}
        />
      </PageShell>
    );
  }

  return (
    <PageShell
      title={isUsers ? "User Administration" : "Activity Logs"}
      eyebrow="Admin"
      description={isUsers ? "Manage platform identities and role assignments." : "Trace who changed what, when, and through which correlation context."}
      actions={canManageUsers ? <button type="button" className="button-primary" onClick={beginCreateUser}>New User</button> : undefined}
    >
      {success ? <div className="rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{success}</div> : null}
      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
      {creatingUser || editingUser ? (
        <section className="panel p-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate">{creatingUser ? "Create User" : "Edit User"}</p>
              <h2 className="mt-1 font-serif text-2xl">{creatingUser ? "New User" : String(editingUser?.username ?? editingUser?.id)}</h2>
            </div>
            <button
              type="button"
              className="button-secondary"
              onClick={() => {
                setCreatingUser(false);
                setEditingUser(null);
                setUserForm(emptyUserForm);
              }}
            >
              Cancel
            </button>
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {creatingUser ? (
              <label className="space-y-2 text-sm font-semibold">
                <span>Username</span>
                <input
                  className="field"
                  value={userForm.username}
                  onChange={(event) => {
                    const value = event.target.value;
                    setUserForm((prev) => ({ ...prev, username: value }));
                  }}
                />
              </label>
            ) : null}
            <label className="space-y-2 text-sm font-semibold">
              <span>Email</span>
              <input
                type="email"
                className="field"
                value={userForm.email}
                onChange={(event) => {
                  const value = event.target.value;
                  setUserForm((prev) => ({ ...prev, email: value }));
                }}
              />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Full Name</span>
              <input
                className="field"
                value={userForm.full_name}
                onChange={(event) => {
                  const value = event.target.value;
                  setUserForm((prev) => ({ ...prev, full_name: value }));
                }}
              />
            </label>
            {creatingUser ? (
              <label className="space-y-2 text-sm font-semibold">
                <span>Password</span>
                <input
                  type="password"
                  className="field"
                  value={userForm.password}
                  onChange={(event) => {
                    const value = event.target.value;
                    setUserForm((prev) => ({ ...prev, password: value }));
                  }}
                />
              </label>
            ) : null}
            <label className="space-y-2 text-sm font-semibold">
              <span>Phone</span>
              <input
                type="text"
                className="field"
                value={userForm.phone}
                onChange={(event) => {
                  const value = event.target.value;
                  setUserForm((prev) => ({ ...prev, phone: value }));
                }}
              />
            </label>
            {renderUserLookupField("designation_id", "Designation", designationOptions)}
            {renderUserLookupField("company_id", "Company", companyOptions)}
            {renderUserLookupField("location_id", "Location", locationOptions)}
            <label className="space-y-2 text-sm font-semibold">
              <span>Active</span>
              <input
                type="checkbox"
                className="h-5 w-5 rounded border-sand text-ink"
                checked={userForm.is_active}
                onChange={(event) => {
                  const checked = event.currentTarget.checked;
                  setUserForm((prev) => ({ ...prev, is_active: checked }));
                }}
              />
            </label>
          </div>
          <fieldset className="mt-5 rounded-2xl border border-sand bg-cream p-4">
            <legend className="px-2 text-sm font-semibold">Role Assignment</legend>
            <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {assignableRoles.map((role) => (
                <label key={role.code} className="flex items-center gap-2 text-sm text-slate">
                  <input
                    type="checkbox"
                    checked={userForm.role_codes.includes(role.code)}
                    onChange={() => setUserForm((prev) => ({ ...prev, role_codes: toggleValue(prev.role_codes, role.code) }))}
                  />
                  <span>{role.name}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <button type="button" className="button-primary mt-5" onClick={handleUserSubmit}>
            Save User
          </button>
        </section>
      ) : null}
      <DataTable
        columns={isUsers ? userColumns : activityColumns}
        data={rows as UserRow[]}
        enableRowSelection={canDeleteUsers}
        selectedRowIds={selectedIds}
        onSelectedRowIdsChange={setSelectedIds}
        getRowId={(row) => String(row.id ?? "")}
        bulkActions={canDeleteUsers && selectedIds.length ? (
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-slate">{selectedIds.length} user(s) selected.</p>
            <button type="button" className="button-danger" onClick={handleBulkDeleteUsers}>
              Delete Selected
            </button>
          </div>
        ) : undefined}
        renderRowActions={canManageUsers || canDeleteUsers ? (row) => (
          <div className="flex flex-wrap gap-2">
            {canManageUsers ? (
              <button type="button" className="button-secondary px-4 py-2" onClick={() => handleEditUser(row)}>
                Edit
              </button>
            ) : null}
            {canDeleteUsers ? (
              <button type="button" className="button-danger" onClick={() => handleDeleteUser(Number(row.id))}>
                Delete
              </button>
            ) : null}
          </div>
        ) : undefined}
      />
    </PageShell>
  );
}
