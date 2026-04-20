from __future__ import annotations

from enum import Enum


class RoleCode(str, Enum):
    SUPER_ADMIN = "super_admin"
    AUDITOR = "auditor"
    HEAD_AUDITOR = "head_auditor"
    MANAGEMENT = "management"
    AUDITEE = "auditee"


class AuditStatus(str, Enum):
    TO_BE_INITIATED = "To be Initiated"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    OVERDUE = "Overdue"
    UNPLANNED = "Unplanned"


class CoverageStatus(str, Enum):
    COVERED = "Covered"
    NOT_COVERED = "Not Covered"


class RiskRating(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    CRITICAL = "Critical"


class ActionPlanStatus(str, Enum):
    PENDING = "Pending to be initiated"
    IN_PROGRESS = "In Progress"
    UNDER_REVIEW = "Under Review"
    COMPLETED = "Completed"
    REOPENED = "Reopened"


class ActivityAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    STATUS_CHANGE = "status_change"
    LOGIN = "login"
    EXPORT = "export"
    UPLOAD = "upload"
    DELETE = "delete"
    ASSIGN = "assign"
    REVIEW = "review"
    RESPOND = "respond"
    IMPORT = "import"


class AttachmentOwnerType(str, Enum):
    ACTION_PLAN = "action_plan"
    ACTION_PLAN_REVISION = "action_plan_revision"
    KNOWLEDGE_LIBRARY = "knowledge_library"
    IMPORT_TEMPLATE = "import_template"


class KnowledgeItemType(str, Enum):
    PROCESS_UNIVERSE = "process_universe"
    RACM = "racm"
    BENCHMARK = "benchmark"
    INITIAL_DATA_REQUEST = "initial_data_request"


class ReportType(str, Enum):
    AUDIT_PLAN = "Audit Plan Report"
    FOLLOW_UP = "Follow Up Report"
    DATA_TRACKER = "Data Tracker Report"
    ACTIVITY = "Activity Report"
