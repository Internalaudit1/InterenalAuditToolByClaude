"use client";

import { Bar, BarChart, CartesianGrid, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Point = { label: string; value: number };

export function DashboardCharts({
  auditStatusSummary,
  actionPlanAging,
  severityDistribution
}: {
  auditStatusSummary: Point[];
  actionPlanAging: Point[];
  severityDistribution: Point[];
}) {
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="panel p-5">
        <h3 className="font-serif text-2xl">Audit Status Summary</h3>
        <div className="mt-4 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={auditStatusSummary}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e7dbc9" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#c25b2c" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="panel p-5">
        <h3 className="font-serif text-2xl">Action Plan Aging</h3>
        <div className="mt-4 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={actionPlanAging} dataKey="value" nameKey="label" outerRadius={90} fill="#53624f" label />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="panel p-5">
        <h3 className="font-serif text-2xl">Severity Distribution</h3>
        <div className="mt-4 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={severityDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e7dbc9" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#53624f" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

