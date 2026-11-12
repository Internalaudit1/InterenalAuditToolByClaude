"use client";

import { ReactElement } from "react";
import { Bar, BarChart, CartesianGrid, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Point = { label: string; value: number };

const EMPTY_MESSAGE = "No data for the selected filters.";

// ResponsiveContainer accepts a single chart element, not arbitrary ReactNode.
function ChartPanel({ title, hasData, children }: { title: string; hasData: boolean; children: ReactElement }) {
  return (
    <div className="panel p-5">
      <h3 className="font-serif text-2xl">{title}</h3>
      {hasData ? (
        <div className="mt-4 h-72">
          <ResponsiveContainer width="100%" height="100%">
            {children}
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="mt-4 flex h-72 items-center justify-center rounded-2xl border border-dashed border-sand">
          <p className="text-sm text-slate">{EMPTY_MESSAGE}</p>
        </div>
      )}
    </div>
  );
}

export function DashboardCharts({
  auditStatusSummary,
  actionPlanAging,
  severityDistribution,
  locationDistribution
}: {
  auditStatusSummary: Point[];
  actionPlanAging: Point[];
  severityDistribution: Point[];
  locationDistribution?: Point[];
}) {
  // An all-zero pie makes recharts place labels at NaN coordinates, so treat it as empty.
  const agingTotal = actionPlanAging.reduce((sum, point) => sum + point.value, 0);
  const locations = locationDistribution ?? [];

  return (
    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
      <ChartPanel title="Audit Status Summary" hasData={auditStatusSummary.length > 0}>
        <BarChart data={auditStatusSummary}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7dbc9" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="value" fill="#c25b2c" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ChartPanel>

      <ChartPanel title="Action Plan Aging" hasData={agingTotal > 0}>
        <PieChart>
          <Pie data={actionPlanAging} dataKey="value" nameKey="label" outerRadius={90} fill="#53624f" label />
          <Tooltip />
        </PieChart>
      </ChartPanel>

      <ChartPanel title="Severity Distribution" hasData={severityDistribution.length > 0}>
        <BarChart data={severityDistribution}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7dbc9" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="value" fill="#53624f" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ChartPanel>

      <ChartPanel title="Audits by Location" hasData={locations.length > 0}>
        <BarChart data={locations}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7dbc9" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="value" fill="#8a6f4a" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ChartPanel>
    </div>
  );
}
