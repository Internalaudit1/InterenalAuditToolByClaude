export type NavItem = {
  label: string;
  href: string;
  permissions: string[];
  children?: NavItem[];
};

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", permissions: ["dashboard:view"] },
  {
    label: "Audit Planning Engine",
    href: "/planning",
    permissions: ["planning:view"],
    children: [
      { label: "Process Risk Mapping", href: "/planning/process-risk-mappings", permissions: ["planning:manage"] },
      { label: "Key ERM Risks", href: "/planning/erm-risks", permissions: ["planning:manage"] },
      { label: "Key Business Initiatives", href: "/planning/business-initiatives", permissions: ["planning:manage"] },
      { label: "Overall Assessment", href: "/planning/overall-assessments", permissions: ["planning:manage"] },
      { label: "Audit Plans", href: "/planning/audit-plans", permissions: ["planning:view"] },
      { label: "Audit Allocation", href: "/audit-allocations", permissions: ["audit_allocations:view"] }
    ]
  },
  { label: "Engagement Planning", href: "/engagement-plans", permissions: ["engagement_plans:view"] },
  { label: "Manage Audits", href: "/audits", permissions: ["audits:view"] },
  { label: "Workpapers", href: "/workpapers", permissions: ["workpapers:view"] },
  { label: "Evidence Register", href: "/evidence", permissions: ["evidence:view"] },
  { label: "My Activities", href: "/activities", permissions: ["audit_activities:view"] },
  { label: "Observations", href: "/observations", permissions: ["observations:view"] },
  { label: "Action Plans", href: "/action-plans", permissions: ["action_plans:view"] },
  { label: "Reports", href: "/reports", permissions: ["reports:view"] },
  {
    label: "Knowledge Library",
    href: "/knowledge-library",
    permissions: ["library:view"],
    children: [
      { label: "Process Universe", href: "/knowledge-library/process-universe", permissions: ["library:view"] },
      { label: "RACM", href: "/knowledge-library/racm", permissions: ["library:view"] },
      { label: "Initial Data Request", href: "/knowledge-library/initial-data-request", permissions: ["library:view"] },
      { label: "Benchmarks", href: "/knowledge-library/benchmarks", permissions: ["library:view"] }
    ]
  },
  {
    label: "Master Data",
    href: "/masters",
    permissions: ["masters:view"],
    children: [
      { label: "Country / State / City", href: "/masters/countries", permissions: ["masters:view"] },
      { label: "States", href: "/masters/states", permissions: ["masters:view"] },
      { label: "Cities", href: "/masters/cities", permissions: ["masters:view"] },
      { label: "Company", href: "/masters/companies", permissions: ["masters:view"] },
      { label: "Process", href: "/masters/processes", permissions: ["masters:view"] },
      { label: "Location", href: "/masters/locations", permissions: ["masters:view"] },
      { label: "Process Location Mapping", href: "/masters/process-location-mappings", permissions: ["masters:view"] },
      { label: "Audit Universe Setup", href: "/masters/audit-universe-setup", permissions: ["masters:manage"] },
      { label: "Risk Type", href: "/masters/risk-types", permissions: ["masters:view"] },
      { label: "Root Cause", href: "/masters/root-causes", permissions: ["masters:view"] },
      { label: "Observation Grading", href: "/masters/observation-gradings", permissions: ["masters:view"] },
      { label: "Report Consideration", href: "/masters/report-considerations", permissions: ["masters:view"] },
      { label: "Recommendation", href: "/masters/recommendations", permissions: ["masters:view"] },
      { label: "Impact", href: "/masters/impacts", permissions: ["masters:view"] },
      { label: "Trial Balance", href: "/masters/trial-balances", permissions: ["masters:view"] },
      { label: "Audit Escalation", href: "/masters/audit-escalations", permissions: ["masters:view"] },
      { label: "Designation", href: "/masters/designations", permissions: ["masters:view"] },
      { label: "Auditees", href: "/masters/auditees", permissions: ["masters:view"] },
      { label: "Control Performance Indicator", href: "/masters/control-performance-indicators", permissions: ["masters:view"] },
      { label: "Task Swap", href: "/masters/task-swaps", permissions: ["masters:view"] }
    ]
  },
  {
    label: "Admin",
    href: "/admin",
    permissions: ["activity_logs:view", "users:view", "roles:view"],
    children: [
      { label: "Activity Logs", href: "/admin/activity-logs", permissions: ["activity_logs:view"] },
      { label: "Users", href: "/admin/users", permissions: ["users:view"] },
      { label: "Roles", href: "/admin/roles", permissions: ["roles:view"] },
      { label: "Data Explorer", href: "/admin/data-explorer", permissions: ["activity_logs:view"] }
    ]
  }
];

export function hasNavAccess(item: NavItem, permissions: string[]) {
  return item.permissions.some((permission) => permissions.includes(permission));
}

export function visibleNavItems(permissions: string[]) {
  const items = NAV_ITEMS
    .map<NavItem | null>((item) => {
      const children = item.children?.filter((child) => hasNavAccess(child, permissions)) ?? [];
      if (!hasNavAccess(item, permissions) && !children.length) {
        return null;
      }
      return { ...item, children };
    })
    .filter((item): item is NavItem => item !== null);
  return items;
}

export function isRouteAllowed(pathname: string, permissions: string[]) {
  return NAV_ITEMS.some((item) => {
    if (hasNavAccess(item, permissions) && !item.children?.length && (pathname === item.href || pathname.startsWith(`${item.href}/`))) return true;
    if (hasNavAccess(item, permissions) && pathname === item.href) return true;
    return item.children?.some((child) => hasNavAccess(child, permissions) && (pathname === child.href || pathname.startsWith(`${child.href}/`)));
  });
}

export function defaultWorkspacePath(permissions: string[]) {
  if (permissions.includes("dashboard:view")) return "/dashboard";
  if (permissions.includes("planning:view")) return "/planning/audit-plans";
  if (permissions.includes("audit_allocations:view")) return "/audit-allocations";
  if (permissions.includes("engagement_plans:view")) return "/engagement-plans";
  if (permissions.includes("audits:view")) return "/audits";
  if (permissions.includes("workpapers:view")) return "/workpapers";
  if (permissions.includes("evidence:view")) return "/evidence";
  if (permissions.includes("audit_activities:view")) return "/activities";
  if (permissions.includes("observations:view")) return "/observations";
  if (permissions.includes("action_plans:view")) return "/action-plans";
  if (permissions.includes("reports:view")) return "/reports";
  return "/forbidden";
}
