import { ColumnDef } from "@tanstack/react-table";

import { ResourceField } from "@/components/resource-page";

type PageConfig = {
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
  editPermission?: string;
  deletePermission?: string;
  importResource?: string;
};

const periodTypeOptions = [
  { label: "Monthly", value: "Monthly" },
  { label: "Quarterly", value: "Quarterly" },
  { label: "Half-Yearly", value: "Half-Yearly" },
  { label: "Annual", value: "Annual" }
];

const periodValueOptions = {
  Monthly: [
    { label: "January", value: "January" },
    { label: "February", value: "February" },
    { label: "March", value: "March" },
    { label: "April", value: "April" },
    { label: "May", value: "May" },
    { label: "June", value: "June" },
    { label: "July", value: "July" },
    { label: "August", value: "August" },
    { label: "September", value: "September" },
    { label: "October", value: "October" },
    { label: "November", value: "November" },
    { label: "December", value: "December" }
  ],
  Quarterly: [
    { label: "Q1", value: "Q1" },
    { label: "Q2", value: "Q2" },
    { label: "Q3", value: "Q3" },
    { label: "Q4", value: "Q4" }
  ],
  "Half-Yearly": [
    { label: "H1", value: "H1" },
    { label: "H2", value: "H2" }
  ],
  Annual: [{ label: "Full Year", value: "Full Year" }]
};

const fiscalYearOptions = Array.from({ length: 18 }, (_, index) => {
  const startYear = 2025 + index;
  return { label: `${startYear}-${startYear + 1}`, value: `${startYear}-${startYear + 1}` };
});

export const planningPageConfig: Record<string, PageConfig> = {
  "process-risk-mappings": {
    title: "Process Risk Mapping",
    eyebrow: "Planning Engine",
    description: "Map process context, trial balance, and qualitative or quantitative ratings into a final process risk view.",
    endpoint: "/planning/process-risk-mappings",
    tableName: "process_risk_mappings",
    createEnabled: true,
    editPermission: "planning:manage",
    deletePermission: "planning:delete",
    fields: [
      { name: "audit_plan_id", label: "Audit Plan ID" },
      { name: "process_location_mapping_id", label: "Process Location Mapping ID" },
      { name: "trial_balance_id", label: "Trial Balance ID" },
      { name: "quantitative_assessment", label: "Quantitative Assessment" },
      { name: "qualitative_assessment", label: "Qualitative Assessment" },
      { name: "final_process_rating", label: "Final Process Rating" }
    ],
    columns: [
      { accessorKey: "audit_plan_id", header: "Audit Plan" },
      { accessorKey: "quantitative_assessment", header: "Quantitative" },
      { accessorKey: "qualitative_assessment", header: "Qualitative" },
      { accessorKey: "final_process_rating", header: "Final Rating" }
    ]
  },
  "erm-risks": {
    title: "Key ERM Risks",
    eyebrow: "Planning Engine",
    description: "Maintain linked enterprise risks and criticality against each audit plan.",
    endpoint: "/planning/erm-risks",
    tableName: "erm_risks",
    createEnabled: true,
    editPermission: "planning:manage",
    deletePermission: "planning:delete",
    fields: [
      { name: "audit_plan_id", label: "Audit Plan ID" },
      { name: "erm_risk_code", label: "Risk Code" },
      { name: "erm_risk_title", label: "Risk Title" },
      { name: "description", label: "Description", type: "textarea" },
      { name: "rating", label: "Rating" },
      { name: "process_id", label: "Process ID" }
    ],
    columns: [
      { accessorKey: "erm_risk_code", header: "Code" },
      { accessorKey: "erm_risk_title", header: "Title" },
      { accessorKey: "rating", header: "Rating" },
      { accessorKey: "process_id", header: "Process ID" }
    ]
  },
  "business-initiatives": {
    title: "Key Business Initiatives",
    eyebrow: "Planning Engine",
    description: "Capture initiative-driven risks and planned ownership that influence audit coverage.",
    endpoint: "/planning/business-initiatives",
    tableName: "business_initiatives",
    createEnabled: true,
    editPermission: "planning:manage",
    deletePermission: "planning:delete",
    fields: [
      { name: "audit_plan_id", label: "Audit Plan ID" },
      { name: "initiative_code", label: "Initiative Code" },
      { name: "title", label: "Title" },
      { name: "description", label: "Description", type: "textarea" },
      { name: "impact", label: "Impact" },
      { name: "owner_user_id", label: "Owner User ID" },
      { name: "timeline", label: "Timeline" }
    ],
    columns: [
      { accessorKey: "initiative_code", header: "Code" },
      { accessorKey: "title", header: "Title" },
      { accessorKey: "impact", header: "Impact" },
      { accessorKey: "timeline", header: "Timeline" }
    ]
  },
  "overall-assessments": {
    title: "Overall Assessment",
    eyebrow: "Planning Engine",
    description: "Evaluate coverage, overall risk, and last-audited context by location.",
    endpoint: "/planning/overall-assessments",
    tableName: "overall_assessments",
    createEnabled: true,
    editPermission: "planning:manage",
    deletePermission: "planning:delete",
    fields: [
      { name: "audit_plan_id", label: "Audit Plan ID" },
      { name: "location_id", label: "Location ID" },
      { name: "overall_risk", label: "Overall Risk" },
      { name: "coverage_status", label: "Coverage Status" },
      { name: "justification", label: "Justification", type: "textarea" },
      { name: "last_audited_date", label: "Last Audited Date", type: "date" }
    ],
    columns: [
      { accessorKey: "audit_plan_id", header: "Audit Plan" },
      { accessorKey: "location_id", header: "Location" },
      { accessorKey: "overall_risk", header: "Overall Risk" },
      { accessorKey: "coverage_status", header: "Coverage" }
    ]
  },
  "audit-plans": {
    title: "Audit Plans",
    eyebrow: "Planning Engine",
    description: "Review the planned audit universe, period distribution, and coverage baseline.",
    endpoint: "/planning/audit-plans",
    tableName: "audit_plans",
    createEnabled: true,
    editPermission: "planning:manage",
    deletePermission: "planning:delete",
    fields: [
      { name: "audit_name", label: "Audit Name" },
      { name: "company_id", label: "Company ID" },
      { name: "location_id", label: "Location ID" },
      { name: "period_type", label: "Period Type", type: "select", options: periodTypeOptions },
      {
        name: "period_value",
        label: "Period Value",
        type: "select",
        dependsOn: "period_type",
        optionsByParent: periodValueOptions,
        disabledPlaceholder: "Select Period Type first"
      },
      { name: "fiscal_year", label: "Fiscal Year", type: "select", options: fiscalYearOptions },
      { name: "start_date", label: "Start Date", type: "date" },
      { name: "end_date", label: "End Date", type: "date" },
      { name: "criticality", label: "Criticality" },
      {
        name: "audit_owner_id",
        label: "Lead Auditor",
        type: "lookup",
        displayField: "audit_owner_name",
        lookup: {
          endpoint: "/admin/users",
          queryParam: "q",
          minChars: 3,
          labelField: "full_name",
          descriptionFields: ["designation_title", "company_name", "location_label"],
          staticParams: { active_only: true, roles: "super_admin,head_auditor,auditor" }
        }
      },
      {
        name: "junior_auditor_1_id",
        label: "Junior Auditor 1",
        type: "lookup",
        displayField: "junior_auditor_1_name",
        lookup: {
          endpoint: "/admin/users",
          queryParam: "q",
          minChars: 3,
          labelField: "full_name",
          descriptionFields: ["designation_title", "company_name", "location_label"],
          staticParams: { active_only: true, roles: "super_admin,head_auditor,auditor,junior_auditor" }
        }
      },
      {
        name: "junior_auditor_2_id",
        label: "Junior Auditor 2",
        type: "lookup",
        displayField: "junior_auditor_2_name",
        lookup: {
          endpoint: "/admin/users",
          queryParam: "q",
          minChars: 3,
          labelField: "full_name",
          descriptionFields: ["designation_title", "company_name", "location_label"],
          staticParams: { active_only: true, roles: "super_admin,head_auditor,auditor,junior_auditor" }
        }
      }
    ],
    columns: [
      { accessorKey: "audit_number", header: "Audit Number" },
      { accessorKey: "audit_name", header: "Audit Name" },
      { accessorKey: "period_type", header: "Period Type" },
      { accessorKey: "period_value", header: "Period Value" },
      { accessorKey: "fiscal_year", header: "FY" },
      { accessorKey: "criticality", header: "Criticality" },
      { accessorKey: "audit_owner_name", header: "Lead Auditor" },
      { accessorKey: "junior_auditor_1_name", header: "Junior Auditor 1" },
      { accessorKey: "junior_auditor_2_name", header: "Junior Auditor 2" },
      { accessorKey: "approval_status", header: "Approval Status" }
    ]
  }
};

export const masterPageConfig: Record<string, PageConfig> = {
  countries: {
    title: "Country / State / City",
    eyebrow: "Master Data",
    description: "Geographic foundation data used by companies, locations, and reporting filters.",
    endpoint: "/master/countries",
    tableName: "countries",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "countries",
    fields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name" },
      { name: "description", label: "Description", type: "textarea" }
    ],
    columns: [
      { accessorKey: "code", header: "Code" },
      { accessorKey: "name", header: "Name" },
      { accessorKey: "description", header: "Description" }
    ]
  },
  states: {
    title: "State Master",
    eyebrow: "Master Data",
    description: "State-level geography referenced by companies and locations.",
    endpoint: "/master/states",
    tableName: "states",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "states",
    fields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name" },
      { name: "country_id", label: "Country" },
      { name: "description", label: "Description", type: "textarea" }
    ],
    columns: [
      { accessorKey: "code", header: "Code" },
      { accessorKey: "name", header: "Name" },
      { accessorKey: "country_id", header: "Country" }
    ]
  },
  cities: {
    title: "City Master",
    eyebrow: "Master Data",
    description: "City-level geography referenced by companies and locations.",
    endpoint: "/master/cities",
    tableName: "cities",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "cities",
    fields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name" },
      { name: "state_id", label: "State" },
      { name: "description", label: "Description", type: "textarea" }
    ],
    columns: [
      { accessorKey: "code", header: "Code" },
      { accessorKey: "name", header: "Name" },
      { accessorKey: "state_id", header: "State" }
    ]
  },
  companies: {
    title: "Company Master",
    eyebrow: "Master Data",
    description: "Maintain legal entities, tax identifiers, and geography links.",
    endpoint: "/master/companies",
    tableName: "companies",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "companies",
    fields: [
      { name: "name", label: "Company Name" },
      { name: "country_id", label: "Country" },
      { name: "state_id", label: "State" },
      { name: "city_id", label: "City" },
      { name: "pan", label: "PAN" },
      { name: "gst_no", label: "GST No" }
    ],
    columns: [
      { accessorKey: "name", header: "Company Name" },
      { accessorKey: "country_id", header: "Country" },
      { accessorKey: "state_id", header: "State" },
      { accessorKey: "city_id", header: "City" }
    ]
  },
  processes: {
    title: "Process Master",
    eyebrow: "Master Data",
    description: "Store sector, business-cycle, and process taxonomy used across planning and reporting.",
    endpoint: "/master/processes",
    tableName: "processes",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "processes",
    fields: [
      { name: "code", label: "Code" },
      { name: "sector", label: "Sector" },
      { name: "business_cycle", label: "Business Cycle" },
      { name: "name", label: "Process Name" },
      { name: "description", label: "Description", type: "textarea" }
    ],
    columns: [
      { accessorKey: "code", header: "Code" },
      { accessorKey: "sector", header: "Sector" },
      { accessorKey: "business_cycle", header: "Business Cycle" },
      { accessorKey: "name", header: "Process" }
    ]
  },
  locations: {
    title: "Location Master",
    eyebrow: "Master Data",
    description: "Maintain location records, sector tags, and risk index by location.",
    endpoint: "/master/locations",
    tableName: "locations",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "locations",
    fields: [
      { name: "sector", label: "Sector" },
      { name: "country_id", label: "Country" },
      { name: "state_id", label: "State" },
      { name: "city_id", label: "City" },
      { name: "company_id", label: "Company" },
      { name: "location_code", label: "Location Code" },
      { name: "risk_index", label: "Risk Index" },
      { name: "description", label: "Description" }
    ],
    columns: [
      { accessorKey: "location_code", header: "Location Code" },
      { accessorKey: "description", header: "Description" },
      { accessorKey: "sector", header: "Sector" },
      { accessorKey: "risk_index", header: "Risk Index" }
    ]
  },
  "process-location-mappings": {
    title: "Process Location Mapping",
    eyebrow: "Master Data",
    description: "Link processes, locations, companies, and trial-balance references.",
    endpoint: "/master/process-location-mappings",
    tableName: "process_location_mappings",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "process-location-mappings",
    fields: [
      { name: "code", label: "Code" },
      { name: "audit_name", label: "Audit Name" },
      { name: "process_id", label: "Process" },
      { name: "location_id", label: "Location" },
      { name: "company_id", label: "Company" },
      { name: "trial_balance_id", label: "Trial Balance" }
    ],
    columns: [
      { accessorKey: "code", header: "Code" },
      { accessorKey: "audit_name", header: "Audit Name" },
      { accessorKey: "process_id", header: "Process" },
      { accessorKey: "location_id", header: "Location" }
    ]
  },
  "risk-types": {
    title: "Risk Types",
    eyebrow: "Master Data",
    description: "Reference list for action plan and planning risk classifications.",
    endpoint: "/master/risk-types",
    tableName: "risk_types",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "risk-types",
    fields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name" },
      { name: "description", label: "Description", type: "textarea" }
    ],
    columns: [
      { accessorKey: "code", header: "Code" },
      { accessorKey: "name", header: "Name" }
    ]
  },
  "root-causes": {
    title: "Root Causes",
    eyebrow: "Master Data",
    description: "Reference list for action plan root-cause assignment.",
    endpoint: "/master/root-causes",
    tableName: "root_causes",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "root-causes",
    fields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name" },
      { name: "description", label: "Description", type: "textarea" }
    ],
    columns: [
      { accessorKey: "code", header: "Code" },
      { accessorKey: "name", header: "Name" }
    ]
  },
  "observation-gradings": {
    title: "Observation Grading",
    eyebrow: "Master Data",
    description: "Severity catalog used in action plans, dashboards, and exports.",
    endpoint: "/master/observation-gradings",
    tableName: "observation_gradings",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "observation-gradings",
    fields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name" },
      { name: "severity_rank", label: "Severity Rank" },
      { name: "description", label: "Description", type: "textarea" }
    ],
    columns: [
      { accessorKey: "code", header: "Code" },
      { accessorKey: "name", header: "Name" },
      { accessorKey: "severity_rank", header: "Rank" }
    ]
  },
  "report-considerations": {
    title: "Report Considerations",
    eyebrow: "Master Data",
    description: "Maintain reporting criteria and considerations used by audit reports.",
    endpoint: "/master/report-considerations",
    tableName: "report_considerations",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "report-considerations"
  },
  recommendations: {
    title: "Recommendations",
    eyebrow: "Master Data",
    description: "Maintain recommendation library records used by audit remediation guidance.",
    endpoint: "/master/recommendations",
    tableName: "recommendations",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "recommendations"
  },
  impacts: {
    title: "Impacts",
    eyebrow: "Master Data",
    description: "Maintain impact categories referenced during issue and reporting analysis.",
    endpoint: "/master/impacts",
    tableName: "impacts",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "impacts"
  },
  "trial-balances": {
    title: "Trial Balances",
    eyebrow: "Master Data",
    description: "Maintain trial balance references used by process-location and risk mapping.",
    endpoint: "/master/trial-balances",
    tableName: "trial_balances",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "trial-balances"
  },
  "audit-escalations": {
    title: "Audit Escalations",
    eyebrow: "Master Data",
    description: "Maintain escalation thresholds and timelines for audit follow-up.",
    endpoint: "/master/audit-escalations",
    tableName: "audit_escalations",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "audit-escalations"
  },
  designations: {
    title: "Designations",
    eyebrow: "Master Data",
    description: "Maintain designation records used by users and task-swap rules.",
    endpoint: "/master/designations",
    tableName: "designations",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "designations"
  },
  auditees: {
    title: "Auditee Master",
    eyebrow: "Master Data",
    description: "Maintain auditee contacts and optionally link them to portal users for response workflows.",
    endpoint: "/master/auditees",
    tableName: "auditees",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    fields: [
      { name: "auditee_code", label: "Auditee Code" },
      { name: "full_name", label: "Full Name" },
      { name: "email", label: "Email" },
      { name: "phone", label: "Phone" },
      { name: "designation", label: "Designation" },
      { name: "department", label: "Department" },
      { name: "company_id", label: "Company" },
      { name: "location_id", label: "Location" },
      {
        name: "linked_user_id",
        label: "Linked Portal User",
        type: "lookup",
        displayField: "linked_user_name",
        lookup: {
          endpoint: "/admin/users",
          queryParam: "q",
          minChars: 3,
          labelField: "full_name",
          descriptionFields: ["designation_title", "company_name", "location_label"],
          staticParams: { active_only: true, role: "auditee" }
        }
      }
    ],
    columns: [
      { accessorKey: "auditee_code", header: "Code" },
      { accessorKey: "full_name", header: "Name" },
      { accessorKey: "email", header: "Email" },
      { accessorKey: "designation", header: "Designation" },
      { accessorKey: "department", header: "Department" }
    ]
  },
  "control-performance-indicators": {
    title: "Control Performance Indicators",
    eyebrow: "Master Data",
    description: "Maintain KPI/CPI definitions used for control and benchmark references.",
    endpoint: "/master/control-performance-indicators",
    tableName: "control_performance_indicators",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "control-performance-indicators"
  },
  "task-swaps": {
    title: "Task Swap Rules",
    eyebrow: "Master Data",
    description: "Maintain designation-based task swap rules and thresholds.",
    endpoint: "/master/task-swaps",
    tableName: "task_swap_rules",
    createEnabled: true,
    editPermission: "masters:manage",
    deletePermission: "masters:delete",
    importResource: "task-swaps"
  }
};

export const knowledgePageConfig: Record<string, PageConfig> = {
  "process-universe": {
    title: "Process Universe",
    eyebrow: "Knowledge Library",
    description: "Sector-tagged process references and starter universe assets.",
    endpoint: "/knowledge-library?item_type=process_universe",
    tableName: "knowledge_library_items",
    columns: [
      { accessorKey: "title", header: "Title" },
      { accessorKey: "category", header: "Category" },
      { accessorKey: "description", header: "Description" }
    ],
    fields: [{ name: "item_type", label: "Item Type" }, { name: "title", label: "Title" }, { name: "description", label: "Description", type: "textarea" }],
    createEnabled: true,
    editPermission: "library:manage",
    deletePermission: "library:delete"
  },
  racm: {
    title: "RACM Library",
    eyebrow: "Knowledge Library",
    description: "Risk and control matrix templates that support audit scoping and testing.",
    endpoint: "/knowledge-library?item_type=racm",
    tableName: "knowledge_library_items",
    columns: [
      { accessorKey: "title", header: "Title" },
      { accessorKey: "category", header: "Category" },
      { accessorKey: "description", header: "Description" }
    ],
    fields: [{ name: "item_type", label: "Item Type" }, { name: "title", label: "Title" }, { name: "description", label: "Description", type: "textarea" }],
    createEnabled: true,
    editPermission: "library:manage",
    deletePermission: "library:delete"
  },
  "initial-data-request": {
    title: "Initial Data Request",
    eyebrow: "Knowledge Library",
    description: "Assumed design: implemented as a real module to replace the broken redirect observed in the baseline tool.",
    endpoint: "/knowledge-library?item_type=initial_data_request",
    tableName: "knowledge_library_items",
    columns: [
      { accessorKey: "title", header: "Title" },
      { accessorKey: "category", header: "Category" },
      { accessorKey: "description", header: "Description" }
    ],
    fields: [{ name: "item_type", label: "Item Type" }, { name: "title", label: "Title" }, { name: "description", label: "Description", type: "textarea" }],
    createEnabled: true,
    editPermission: "library:manage",
    deletePermission: "library:delete"
  },
  benchmarks: {
    title: "Benchmarks",
    eyebrow: "Knowledge Library",
    description: "Reference benchmarks and comparative performance indicators for audit analytics.",
    endpoint: "/knowledge-library?item_type=benchmark",
    tableName: "knowledge_library_items",
    columns: [
      { accessorKey: "title", header: "Title" },
      { accessorKey: "category", header: "Category" },
      { accessorKey: "description", header: "Description" }
    ],
    fields: [{ name: "item_type", label: "Item Type" }, { name: "title", label: "Title" }, { name: "description", label: "Description", type: "textarea" }],
    createEnabled: true,
    editPermission: "library:manage",
    deletePermission: "library:delete"
  }
};
