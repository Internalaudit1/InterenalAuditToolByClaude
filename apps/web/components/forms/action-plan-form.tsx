"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { PageShell } from "@/components/layout/page-shell";
import { apiFetch } from "@/lib/api";

const schema = z.object({
  audit_id: z.coerce.number().min(1),
  location_id: z.coerce.number().min(1),
  observation_heading: z.string().min(3),
  observation_grading_id: z.coerce.number().min(1),
  detailed_observation: z.string().min(10),
  risk_type_id: z.coerce.number().min(1),
  agreed_timeline: z.string().min(1),
  review_quarter: z.string().min(1),
  responsibility_department: z.string().min(1),
  implementation_owner_user_id: z.coerce.number().min(1),
  assigned_auditor_user_id: z.coerce.number().min(1),
  root_cause_id: z.coerce.number().min(1),
  auditor_status: z.string().min(1),
  auditee_status: z.string().min(1),
  auditor_implementation_remarks: z.string().optional().default(""),
  management_response: z.string().optional().default(""),
  agreed_action_plan: z.string().optional().default("")
});

type FormValues = z.infer<typeof schema>;

type Option = { id: number; label: string; audit_number?: string };

export function ActionPlanForm() {
  const router = useRouter();
  const [audits, setAudits] = useState<Option[]>([]);
  const [locations, setLocations] = useState<Option[]>([]);
  const [gradings, setGradings] = useState<Option[]>([]);
  const [riskTypes, setRiskTypes] = useState<Option[]>([]);
  const [rootCauses, setRootCauses] = useState<Option[]>([]);
  const [users, setUsers] = useState<Option[]>([]);
  const [error, setError] = useState("");
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting }
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      auditor_status: "Pending to be initiated",
      auditee_status: "Pending to be initiated"
    }
  });

  useEffect(() => {
    Promise.all([
      apiFetch<{ items: { id: number; audit_name: string; audit_number: string }[] }>("/audits?page_size=50"),
      apiFetch<{ items: { id: number; description: string }[] }>("/master/locations?page_size=50"),
      apiFetch<{ items: { id: number; name: string }[] }>("/master/observation-gradings?page_size=50"),
      apiFetch<{ items: { id: number; name: string }[] }>("/master/risk-types?page_size=50"),
      apiFetch<{ items: { id: number; name: string }[] }>("/master/root-causes?page_size=50"),
      apiFetch<{ id: number; full_name: string }[]>("/admin/users")
    ])
      .then(([auditsData, locationsData, gradingsData, riskTypesData, rootCausesData, usersData]) => {
        setAudits(auditsData.items.map((item) => ({ id: item.id, label: item.audit_name, audit_number: item.audit_number })));
        setLocations(locationsData.items.map((item) => ({ id: item.id, label: item.description })));
        setGradings(gradingsData.items.map((item) => ({ id: item.id, label: item.name })));
        setRiskTypes(riskTypesData.items.map((item) => ({ id: item.id, label: item.name })));
        setRootCauses(rootCausesData.items.map((item) => ({ id: item.id, label: item.name })));
        setUsers(usersData.map((item) => ({ id: item.id, label: item.full_name })));
      })
      .catch((err) => setError((err as Error).message));
  }, []);

  const selectedAudit = audits.find((item) => item.id === Number(watch("audit_id")));

  return (
    <PageShell title="New Action Plan" eyebrow="Workflow Control" description="Create a maker-checker compliant action plan. The backend will enforce that the auditee cannot own auditor-side transitions.">
      <form
        className="panel space-y-6 p-6"
        onSubmit={handleSubmit(async (values) => {
          setError("");
          try {
            await apiFetch("/action-plans", {
              method: "POST",
              body: JSON.stringify({
                ...values,
                revised_date: values.agreed_timeline
              })
            });
            router.push("/action-plans");
          } catch (err) {
            setError((err as Error).message);
          }
        })}
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label className="space-y-2 text-sm font-semibold">
            <span>Select Audit</span>
            <select
              className="field"
              {...register("audit_id")}
              onChange={(event) => {
                setValue("audit_id", Number(event.target.value));
              }}
            >
              <option value="">Select Audit</option>
              {audits.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
            {errors.audit_id ? <p className="text-sm text-ember">{errors.audit_id.message}</p> : null}
          </label>
          <div className="space-y-2 text-sm font-semibold">
            <span>Audit Number</span>
            <div className="field flex items-center bg-mist text-slate">
              {selectedAudit?.audit_number ?? "Select an audit to view the generated number"}
            </div>
          </div>
          <label className="space-y-2 text-sm font-semibold">
            <span>Location</span>
            <select className="field" {...register("location_id")}>
              <option value="">Select Location</option>
              {locations.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2 text-sm font-semibold md:col-span-2">
            <span>Observation Heading</span>
            <input className="field" {...register("observation_heading")} />
          </label>
          <label className="space-y-2 text-sm font-semibold">
            <span>Observation Grading</span>
            <select className="field" {...register("observation_grading_id")}>
              <option value="">Select Grading</option>
              {gradings.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2 text-sm font-semibold">
            <span>Risk Type</span>
            <select className="field" {...register("risk_type_id")}>
              <option value="">Select Risk Type</option>
              {riskTypes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2 text-sm font-semibold">
            <span>Root Cause</span>
            <select className="field" {...register("root_cause_id")}>
              <option value="">Select Root Cause</option>
              {rootCauses.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2 text-sm font-semibold">
            <span>Agreed Timeline</span>
            <input type="date" className="field" {...register("agreed_timeline")} />
          </label>
          <label className="space-y-2 text-sm font-semibold">
            <span>Review Quarter</span>
            <input className="field" {...register("review_quarter")} placeholder="Q1" />
          </label>
          <div className="space-y-2 text-sm font-semibold">
            <span>Observation Number</span>
            <div className="field flex items-center bg-mist text-slate">Auto-generated after save</div>
          </div>
          <label className="space-y-2 text-sm font-semibold">
            <span>Department</span>
            <input className="field" {...register("responsibility_department")} />
          </label>
          <label className="space-y-2 text-sm font-semibold">
            <span>Implementation Owner</span>
            <select className="field" {...register("implementation_owner_user_id")}>
              <option value="">Select Owner</option>
              {users.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2 text-sm font-semibold">
            <span>Assigned Auditor</span>
            <select className="field" {...register("assigned_auditor_user_id")}>
              <option value="">Select Auditor</option>
              {users.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2 text-sm font-semibold md:col-span-3">
            <span>Detailed Observation</span>
            <textarea className="field min-h-32" {...register("detailed_observation")} />
          </label>
          <label className="space-y-2 text-sm font-semibold md:col-span-3">
            <span>Auditor Implementation Remarks</span>
            <textarea className="field min-h-28" {...register("auditor_implementation_remarks")} />
          </label>
        </div>
        {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}
        <button disabled={isSubmitting} className="button-primary">
          {isSubmitting ? "Creating..." : "Create Action Plan"}
        </button>
      </form>
    </PageShell>
  );
}
