"use client";

import { useEffect, useState } from "react";

import { DashboardCharts } from "@/components/charts/dashboard-charts";
import { PageShell } from "@/components/layout/page-shell";
import { StatGrid } from "@/components/stat-grid";
import { apiFetch } from "@/lib/api";

type DashboardSummary = {
  total_audits: number;
  in_progress: number;
  completed: number;
  overdue: number;
  pending_to_be_initiated: number;
  total_action_plans: number;
  audit_status_summary: { label: string; value: number }[];
  action_plan_aging: { label: string; value: number }[];
  severity_distribution: { label: string; value: number }[];
  location_distribution: { label: string; value: number }[];
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    apiFetch<DashboardSummary>("/dashboard/summary").then(setData).catch(console.error);
  }, []);

  return (
    <PageShell title="Executive Dashboard" eyebrow="Command Center" description="A fully in-app analytics view, replacing the Power BI shell dependency observed in the source tool.">
      <StatGrid
        items={[
          { label: "Total Audits", value: data?.total_audits ?? 0 },
          { label: "In Progress", value: data?.in_progress ?? 0 },
          { label: "Completed", value: data?.completed ?? 0 },
          { label: "Overdue", value: data?.overdue ?? 0 },
          { label: "Pending", value: data?.pending_to_be_initiated ?? 0 },
          { label: "Action Plans", value: data?.total_action_plans ?? 0 }
        ]}
      />
      {data ? (
        <DashboardCharts
          auditStatusSummary={data.audit_status_summary}
          actionPlanAging={data.action_plan_aging}
          severityDistribution={data.severity_distribution}
        />
      ) : null}
    </PageShell>
  );
}

