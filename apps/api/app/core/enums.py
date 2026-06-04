from __future__ import annotations

from enum import Enum


class RoleCode(str, Enum):
    SUPER_ADMIN = "super_admin"
    AUDITOR = "auditor"
    JUNIOR_AUDITOR = "junior_auditor"
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
    APPROVE = "approve"
    ISSUE = "issue"
    CONVERT = "convert"


class AuditPlanApprovalStatus(str, Enum):
    DRAFT = "Draft"
    UNDER_REVIEW = "Under Review"
    APPROVED = "Approved"
    DEFERRED = "Deferred"
    CANCELLED = "Cancelled"


class AuditMembershipRole(str, Enum):
    LEAD_AUDITOR = "lead_auditor"
    JUNIOR_AUDITOR = "junior_auditor"
    REVIEWER = "reviewer"
    AUDITEE_SPOC = "auditee_spoc"
    OBSERVER = "observer"


class AuditActivityStatus(str, Enum):
    YET_TO_START = "Yet to Start"
    WORK_IN_PROGRESS = "Work in Progress"
    COMPLETED = "Completed"
    NOT_APPLICABLE = "Not Applicable"


class ObservationStatus(str, Enum):
    DRAFT = "Draft"
    ISSUED = "Issued"
    RESPONDED = "Responded"
    ACCEPTED = "Accepted"
    CONVERTED = "Converted"
    DROPPED = "Dropped"


class EngagementPlanStatus(str, Enum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    KICKED_OFF = "Kicked Off"


class EngagementResourceRole(str, Enum):
    LEAD_AUDITOR = "Lead Auditor"
    REVIEWER = "Reviewer"
    JUNIOR_AUDITOR = "Junior Auditor"
    AUDIT_SUPPORT = "Audit Support"
    AUDITEE_SPOC = "Auditee SPOC"
    OBSERVER = "Observer"


class EngagementDocumentType(str, Enum):
    ENGAGEMENT_LETTER = "Engagement Letter"
    SCOPE_MEMO = "Scope Memo"
    KICKOFF_MINUTES = "Kickoff Minutes"
    RESOURCE_PLAN = "Resource Plan"
    BUDGET_WORKBOOK = "Budget Workbook"
    OTHER = "Other"


class WorkpaperStatus(str, Enum):
    DRAFT = "Draft"
    SUBMITTED_FOR_REVIEW = "Submitted for Review"
    REVIEWED = "Reviewed"
    APPROVED = "Approved"
    LOCKED = "Locked"


class WorkpaperReviewStatus(str, Enum):
    REVIEWED = "Reviewed"
    APPROVED = "Approved"
    LOCKED = "Locked"


class EvidenceConfidentialityLevel(str, Enum):
    INTERNAL = "Internal"
    CONFIDENTIAL = "Confidential"
    RESTRICTED = "Restricted"
    HIGHLY_RESTRICTED = "Highly Restricted"


class AuditEventType(str, Enum):
    AUDIT_INITIATED = "audit_initiated"
    STATUS_CHANGED = "status_changed"
    MEMBER_ASSIGNED = "member_assigned"
    MEMBER_REMOVED = "member_removed"
    ENGAGEMENT_CREATED = "engagement_created"
    ENGAGEMENT_SUBMITTED = "engagement_submitted"
    ENGAGEMENT_APPROVED = "engagement_approved"
    ENGAGEMENT_REJECTED = "engagement_rejected"
    ENGAGEMENT_KICKED_OFF = "engagement_kicked_off"
    WORKPAPER_CREATED = "workpaper_created"
    WORKPAPER_SUBMITTED = "workpaper_submitted"
    WORKPAPER_REVIEWED = "workpaper_reviewed"
    WORKPAPER_APPROVED = "workpaper_approved"
    WORKPAPER_LOCKED = "workpaper_locked"
    EVIDENCE_REGISTERED = "evidence_registered"
    EVIDENCE_LINKED = "evidence_linked"


class NotificationOutboxStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    FAILED = "failed"


class AttachmentOwnerType(str, Enum):
    ACTION_PLAN = "action_plan"
    ACTION_PLAN_REVISION = "action_plan_revision"
    KNOWLEDGE_LIBRARY = "knowledge_library"
    IMPORT_TEMPLATE = "import_template"
    WORKPAPER_VERSION = "workpaper_version"
    EVIDENCE_REGISTER = "evidence_register"


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
