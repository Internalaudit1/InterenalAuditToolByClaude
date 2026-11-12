"use client";

import { useEffect, useMemo, useState } from "react";

import { DashboardCharts } from "@/components/charts/dashboard-charts";
import { PageShell } from "@/components/layout/page-shell";
import { StatGrid } from "@/components/stat-grid";
import { apiFetch } from "@/lib/api";

type ChartPoint = { label: string; value: number };

type DashboardSummary = {
  total_audits: number;
  in_progress: number;
  completed: number;
  overdue: number;
  pending_to_be_initiated: number;
  unplanned: number;
  past_due_count: number;
  total_action_plans: number;
  audit_status_summary: ChartPoint[];
  action_plan_aging: ChartPoint[];
  severity_distribution: ChartPoint[];
  location_distribution: ChartPoint[];
};

type FilterOption = { id: number; label: string };
type LocationOption = FilterOption & { company_id: number };

type FilterOptions = {
  fiscal_years: string[];
  statuses: string[];
  companies: FilterOption[];
  locations: LocationOption[];
};

type Filters = {
  fiscal_year: string;
  status: string;
  company_id: string;
  location_id: string;
};

const EMPTY_FILTERS: Filters = { fiscal_year: "", status: "", company_id: "", location_id: "" };

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [options, setOptions] = useState<FilterOptions | null>(null);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const query = useMemo(() => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    const queryString = params.toString();
    return queryString ? `?${queryString}` : "";
  }, [filters]);

  const filtersApplied = query.length > 0;

  useEffect(() => {
    apiFetch<FilterOptions>("/dashboard/filter-options")
      .then(setOptions)
      .catch(() => setOptions(null));
  }, []);

  useEffect(() => {
    // `cancelled` keeps a slow earlier response from overwriting a newer one when
    // filters are changed quickly.
    let cancelled = false;
    setLoading(true);
    apiFetch<DashboardSummary>(`/dashboard/summary${query}`)
      .then((summary) => {
        if (cancelled) return;
        setData(summary);
        setError("");
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message || "Unable to load the dashboard.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [query]);

  const scopedLocations = useMemo(() => {
    const all = options?.locations ?? [];
    if (!filters.company_id) return all;
    return all.filter((location) => String(location.company_id) === filters.company_id);
  }, [options, filters.company_id]);

  // Status cards are built from the same array that feeds the chart, so the two can never disagree.
  const statusCards = (data?.audit_status_summary ?? []).map((point) => ({
    label: point.label,
    value: point.value,
    hint:
      point.label === "Overdue" && data
        ? `${data.past_due_count} past end date`
        : undefined
  }));

  return (
    <PageShell
      title="Executive Dashboard"
      eyebrow="Command Center"
      description="Every card and chart below reflects the filters you select. Audit Status filters by the status of the audit, so action-plan figures show the plans belonging to those audits."
      actions={
        <button
          type="button"
          className="button-secondary"
          disabled={!filtersApplied}
          onClick={() => setFilters(EMPTY_FILTERS)}
        >
          Reset Filters
        </button>
      }
    >
      <section className="panel p-5">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <label className="space-y-2 text-sm font-semibold">
            <span>Fiscal Year</span>
            <select
              className="field"
              value={filters.fiscal_year}
              onChange={(event) => setFilters((prev) => ({ ...prev, fiscal_year: event.target.value }))}
            >
              <option value="">All Fiscal Years</option>
              {(options?.fiscal_years ?? []).map((fiscalYear) => (
                <option key={fiscalYear} value={fiscalYear}>
                  {fiscalYear}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-2 text-sm font-semibold">
            <span>Audit Status</span>
            <select
              className="field"
              value={filters.status}
              onChange={(event) => setFilters((prev) => ({ ...prev, status: event.target.value }))}
            >
              <option value="">All Statuses</option>
              {(options?.statuses ?? []).map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-2 text-sm font-semibold">
            <span>Company</span>
            <select
              className="field"
              value={filters.company_id}
              onChange={(event) =>
                // Clear location in the same update so we never request a mismatched pair.
                setFilters((prev) => ({ ...prev, company_id: event.target.value, location_id: "" }))
              }
            >
              <option value="">All Companies</option>
              {(options?.companies ?? []).map((company) => (
                <option key={company.id} value={company.id}>
                  {company.label}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-2 text-sm font-semibold">
            <span>Location</span>
            <select
              className="field"
              value={filters.location_id}
              onChange={(event) => setFilters((prev) => ({ ...prev, location_id: event.target.value }))}
            >
              <option value="">All Locations</option>
              {scopedLocations.map((location) => (
                <option key={location.id} value={location.id}>
                  {location.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        {loading ? <p className="mt-4 text-sm text-slate">Updating...</p> : null}
      </section>

      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}

      <StatGrid
        items={[
          { label: "Total Audits", value: data?.total_audits ?? 0 },
          ...statusCards,
          { label: "Action Plans", value: data?.total_action_plans ?? 0 }
        ]}
      />

      {data ? (
        <DashboardCharts
          auditStatusSummary={data.audit_status_summary}
          actionPlanAging={data.action_plan_aging}
          severityDistribution={data.severity_distribution}
          locationDistribution={data.location_distribution}
        />
      ) : null}
    </PageShell>
  );
}
