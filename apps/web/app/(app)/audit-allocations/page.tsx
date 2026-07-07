"use client";

import { useEffect, useMemo, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { apiFetch } from "@/lib/api";
import { hasPermission } from "@/lib/auth";

type UserOption = { id: number; full_name: string; username: string };
type AvailablePlan = {
  id: number;
  audit_number: string;
  audit_name: string;
  audit_area?: string | null;
  fiscal_year: string;
  criticality?: string | null;
};
type Allocation = {
  id: number;
  allocation_code: string;
  audit_plan_number?: string | null;
  audit_plan_name?: string | null;
  lead_auditor_name?: string | null;
  junior_auditor_1_name?: string | null;
  mentor_name?: string | null;
  period_type?: string | null;
  period_value?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  status: string;
  audit_id?: number | null;
};

const PERIOD_TYPES = ["Monthly", "Quarterly", "Half-Yearly", "Annual"];

const emptyForm = {
  audit_plan_id: "",
  lead_auditor_user_id: "",
  junior_auditor_1_id: "",
  junior_auditor_2_id: "",
  mentor_user_id: "",
  period_type: "Quarterly",
  period_value: "",
  start_date: "",
  end_date: ""
};

export default function AuditAllocationsPage() {
  const [allocations, setAllocations] = useState<Allocation[]>([]);
  const [plans, setPlans] = useState<AvailablePlan[]>([]);
  const [users, setUsers] = useState<UserOption[]>([]);
  const [form, setForm] = useState({ ...emptyForm });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const canManage = hasPermission("audit_allocations:manage");
  const canApprove = hasPermission("audit_allocations:approve");

  async function load() {
    try {
      const list = await apiFetch<{ items: Allocation[] }>("/planning/audit-allocations?page_size=100");
      setAllocations(list.items);
      if (canManage) {
        const [availablePlans, userList] = await Promise.all([
          apiFetch<AvailablePlan[]>("/planning/audit-allocations/available-plans"),
          apiFetch<UserOption[]>("/admin/users").catch(() => [])
        ]);
        setPlans(availablePlans);
        setUsers(userList);
      }
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function update(field: keyof typeof emptyForm, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function createAllocation() {
    setError("");
    setSuccess("");
    try {
      const payload: Record<string, unknown> = {
        audit_plan_id: Number(form.audit_plan_id),
        lead_auditor_user_id: Number(form.lead_auditor_user_id),
        period_type: form.period_type || null,
        period_value: form.period_value || null,
        start_date: form.start_date || null,
        end_date: form.end_date || null
      };
      if (form.junior_auditor_1_id) payload.junior_auditor_1_id = Number(form.junior_auditor_1_id);
      if (form.junior_auditor_2_id) payload.junior_auditor_2_id = Number(form.junior_auditor_2_id);
      if (form.mentor_user_id) payload.mentor_user_id = Number(form.mentor_user_id);
      await apiFetch("/planning/audit-allocations", { method: "POST", body: JSON.stringify(payload) });
      setForm({ ...emptyForm });
      setSuccess("Allocation created.");
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function act(id: number, action: "approve" | "initiate-audit") {
    setError("");
    setSuccess("");
    try {
      await apiFetch(`/planning/audit-allocations/${id}/${action}`, { method: "POST", body: JSON.stringify({}) });
      setSuccess(action === "approve" ? "Allocation approved." : "Audit initiated from allocation.");
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const canSubmit = useMemo(
    () => Boolean(form.audit_plan_id && form.lead_auditor_user_id),
    [form.audit_plan_id, form.lead_auditor_user_id]
  );

  return (
    <PageShell
      title="Audit Allocation"
      eyebrow="Audit Planning Engine"
      description="Assign approved audit plans to a lead auditor, junior auditors and mentor, then initiate the audit. The audit plan itself stays fixed and locked after approval."
    >
      {error ? <div className="panel border-l-4 border-rose-500 p-4 text-sm text-rose-600">{error}</div> : null}
      {success ? <div className="panel border-l-4 border-emerald-500 p-4 text-sm text-emerald-600">{success}</div> : null}

      {canManage ? (
        <section className="panel space-y-4 p-5">
          <h2 className="text-lg font-semibold">New allocation</h2>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <label className="space-y-1 text-sm">
              <span className="text-slate">Audit plan (approved)</span>
              <select className="input w-full" value={form.audit_plan_id} onChange={(e) => update("audit_plan_id", e.target.value)}>
                <option value="">Select an approved audit plan…</option>
                {plans.map((plan) => (
                  <option key={plan.id} value={plan.id}>
                    {plan.audit_number} — {plan.audit_area ?? plan.audit_name} ({plan.fiscal_year})
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate">Lead auditor</span>
              <select className="input w-full" value={form.lead_auditor_user_id} onChange={(e) => update("lead_auditor_user_id", e.target.value)}>
                <option value="">Select lead auditor…</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate">Mentor (reviewer)</span>
              <select className="input w-full" value={form.mentor_user_id} onChange={(e) => update("mentor_user_id", e.target.value)}>
                <option value="">Optional…</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate">Junior auditor 1</span>
              <select className="input w-full" value={form.junior_auditor_1_id} onChange={(e) => update("junior_auditor_1_id", e.target.value)}>
                <option value="">Optional…</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate">Junior auditor 2 (optional)</span>
              <select className="input w-full" value={form.junior_auditor_2_id} onChange={(e) => update("junior_auditor_2_id", e.target.value)}>
                <option value="">Optional…</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate">Period type</span>
              <select className="input w-full" value={form.period_type} onChange={(e) => update("period_type", e.target.value)}>
                {PERIOD_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate">Period value (e.g. Q1)</span>
              <input className="input w-full" value={form.period_value} onChange={(e) => update("period_value", e.target.value)} placeholder="Q1" />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate">Commencement date</span>
              <input type="date" className="input w-full" value={form.start_date} onChange={(e) => update("start_date", e.target.value)} />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate">Expected completion date</span>
              <input type="date" className="input w-full" value={form.end_date} onChange={(e) => update("end_date", e.target.value)} />
            </label>
          </div>
          <button className="button-primary" disabled={!canSubmit} onClick={createAllocation}>
            Create allocation
          </button>
        </section>
      ) : null}

      <section className="panel overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate">
              <th className="p-3">Allocation</th>
              <th className="p-3">Audit plan</th>
              <th className="p-3">Lead</th>
              <th className="p-3">Mentor</th>
              <th className="p-3">Period</th>
              <th className="p-3">Dates</th>
              <th className="p-3">Status</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {allocations.map((a) => (
              <tr key={a.id} className="border-b border-slate-100">
                <td className="p-3 font-medium">{a.allocation_code}</td>
                <td className="p-3">{a.audit_plan_number} — {a.audit_plan_name}</td>
                <td className="p-3">{a.lead_auditor_name ?? "--"}</td>
                <td className="p-3">{a.mentor_name ?? "--"}</td>
                <td className="p-3">{[a.period_type, a.period_value].filter(Boolean).join(" ") || "--"}</td>
                <td className="p-3">{[a.start_date, a.end_date].filter(Boolean).join(" → ") || "--"}</td>
                <td className="p-3">{a.status}</td>
                <td className="p-3 space-x-2">
                  {canApprove && a.status === "Draft" ? (
                    <button className="button-secondary" onClick={() => act(a.id, "approve")}>Approve</button>
                  ) : null}
                  {canApprove && a.status === "Allocated" ? (
                    <button className="button-primary" onClick={() => act(a.id, "initiate-audit")}>Initiate audit</button>
                  ) : null}
                  {a.status === "Initiated" ? <span className="text-slate">Audit #{a.audit_id}</span> : null}
                </td>
              </tr>
            ))}
            {allocations.length === 0 ? (
              <tr>
                <td className="p-4 text-slate" colSpan={8}>No allocations yet.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>
    </PageShell>
  );
}
