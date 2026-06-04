from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import EvidenceConfidentialityLevel, WorkpaperReviewStatus, WorkpaperStatus
from app.schemas.base import BaseResponse


class WorkpaperFields(BaseModel):
    audit_id: int
    activity_id: int | None = None
    observation_id: int | None = None
    test_procedure_id: int | None = None
    title: str
    folder_path: str | None = None
    owner_user_id: int | None = None
    reviewer_user_id: int | None = None


class WorkpaperCreate(WorkpaperFields):
    model_config = ConfigDict(extra="forbid")


class WorkpaperUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: int | None = None
    observation_id: int | None = None
    test_procedure_id: int | None = None
    title: str | None = None
    folder_path: str | None = None
    owner_user_id: int | None = None
    reviewer_user_id: int | None = None


class WorkpaperSubmitReviewRequest(BaseModel):
    comment: str | None = None


class WorkpaperReviewRequest(BaseModel):
    review_status: WorkpaperReviewStatus
    review_comment: str | None = None


class WorkpaperVersionResponse(BaseResponse):
    workpaper_id: int
    version_no: int
    document_id: int
    change_summary: str | None = None
    uploaded_by_user_id: int | None = None
    uploaded_by_name: str | None = None
    uploaded_at: datetime
    hash_checksum: str


class WorkpaperReviewResponse(BaseResponse):
    workpaper_id: int
    reviewer_user_id: int | None = None
    reviewer_name: str | None = None
    review_status: WorkpaperReviewStatus
    review_comment: str | None = None
    reviewed_at: datetime


class WorkpaperResponse(BaseResponse, WorkpaperFields):
    workpaper_code: str
    company_id: int
    location_id: int
    status: WorkpaperStatus
    current_version_no: int
    owner_name: str | None = None
    reviewer_name: str | None = None
    signoff_at: datetime | None = None


class WorkpaperDetailResponse(WorkpaperResponse):
    versions: list[WorkpaperVersionResponse] = []
    reviews: list[WorkpaperReviewResponse] = []
    linked_evidence_ids: list[int] = []


class EvidenceLinkCreate(BaseModel):
    linked_module: str
    linked_record_id: int


class EvidenceLinkResponse(BaseResponse):
    evidence_id: int
    linked_module: str
    linked_record_id: int


class EvidenceResponse(BaseResponse):
    evidence_code: str
    audit_id: int
    company_id: int
    location_id: int
    activity_id: int | None = None
    source_type: str
    source_name: str
    evidence_description: str | None = None
    document_id: int
    collected_by_user_id: int | None = None
    collected_by_name: str | None = None
    collected_at: datetime
    confidentiality_level: EvidenceConfidentialityLevel


class EvidenceDetailResponse(EvidenceResponse):
    links: list[EvidenceLinkResponse] = []
