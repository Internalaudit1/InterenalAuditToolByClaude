from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Workpaper(BaseModel):
    __tablename__ = "workpapers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Draft', 'Submitted for Review', 'Reviewed', 'Approved', 'Locked')",
            name="ck_workpapers_status_valid",
        ),
        CheckConstraint("current_version_no >= 0", name="ck_workpapers_version_non_negative"),
        Index("ix_workpapers_audit_activity_status", "audit_id", "activity_id", "status"),
        Index("ix_workpapers_company_location", "company_id", "location_id"),
    )

    workpaper_code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("audit_activities.id"), nullable=True, index=True)
    observation_id: Mapped[int | None] = mapped_column(ForeignKey("observations.id"), nullable=True, index=True)
    test_procedure_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    folder_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Draft", nullable=False)
    current_version_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    reviewer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    signoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    audit: Mapped["Audit"] = relationship("Audit")
    company: Mapped["Company"] = relationship("Company")
    location: Mapped["Location"] = relationship("Location")
    activity: Mapped["AuditActivity | None"] = relationship("AuditActivity")
    observation: Mapped["Observation | None"] = relationship("Observation")
    owner_user: Mapped["User | None"] = relationship("User", foreign_keys=[owner_user_id])
    reviewer_user: Mapped["User | None"] = relationship("User", foreign_keys=[reviewer_user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
    versions: Mapped[list["WorkpaperVersion"]] = relationship("WorkpaperVersion", back_populates="workpaper", cascade="all, delete-orphan")
    reviews: Mapped[list["WorkpaperReview"]] = relationship("WorkpaperReview", back_populates="workpaper", cascade="all, delete-orphan")

    @property
    def owner_name(self) -> str | None:
        return self.owner_user.full_name if self.owner_user else None

    @property
    def reviewer_name(self) -> str | None:
        return self.reviewer_user.full_name if self.reviewer_user else None


class WorkpaperVersion(BaseModel):
    __tablename__ = "workpaper_versions"
    __table_args__ = (
        UniqueConstraint("workpaper_id", "version_no", name="uq_workpaper_versions_workpaper_version"),
        Index("ix_workpaper_versions_workpaper_uploaded", "workpaper_id", "uploaded_at"),
    )

    workpaper_id: Mapped[int] = mapped_column(ForeignKey("workpapers.id"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    hash_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    workpaper: Mapped[Workpaper] = relationship("Workpaper", back_populates="versions")
    document: Mapped["Attachment"] = relationship("Attachment")
    uploaded_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[uploaded_by_user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])

    @property
    def uploaded_by_name(self) -> str | None:
        return self.uploaded_by_user.full_name if self.uploaded_by_user else None


class WorkpaperReview(BaseModel):
    __tablename__ = "workpaper_reviews"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('Reviewed', 'Approved', 'Locked')",
            name="ck_workpaper_reviews_status_valid",
        ),
        Index("ix_workpaper_reviews_workpaper_reviewed", "workpaper_id", "reviewed_at"),
    )

    workpaper_id: Mapped[int] = mapped_column(ForeignKey("workpapers.id"), nullable=False, index=True)
    reviewer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    review_status: Mapped[str] = mapped_column(String(50), nullable=False)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    workpaper: Mapped[Workpaper] = relationship("Workpaper", back_populates="reviews")
    reviewer_user: Mapped["User | None"] = relationship("User", foreign_keys=[reviewer_user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])

    @property
    def reviewer_name(self) -> str | None:
        return self.reviewer_user.full_name if self.reviewer_user else None


class EvidenceRegister(BaseModel):
    __tablename__ = "evidence_register"
    __table_args__ = (
        CheckConstraint(
            "confidentiality_level IN ('Internal', 'Confidential', 'Restricted', 'Highly Restricted')",
            name="ck_evidence_register_confidentiality_valid",
        ),
        Index("ix_evidence_register_audit_activity", "audit_id", "activity_id"),
        Index("ix_evidence_register_company_location", "company_id", "location_id"),
    )

    evidence_code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("audit_activities.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"), nullable=False)
    collected_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    confidentiality_level: Mapped[str] = mapped_column(String(50), default="Internal", nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    audit: Mapped["Audit"] = relationship("Audit")
    company: Mapped["Company"] = relationship("Company")
    location: Mapped["Location"] = relationship("Location")
    activity: Mapped["AuditActivity | None"] = relationship("AuditActivity")
    document: Mapped["Attachment"] = relationship("Attachment")
    collected_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[collected_by_user_id])
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
    links: Mapped[list["EvidenceLink"]] = relationship("EvidenceLink", back_populates="evidence", cascade="all, delete-orphan")

    @property
    def collected_by_name(self) -> str | None:
        return self.collected_by_user.full_name if self.collected_by_user else None


class EvidenceLink(BaseModel):
    __tablename__ = "evidence_links"
    __table_args__ = (
        CheckConstraint(
            "linked_module IN ('workpaper', 'observation', 'test_procedure')",
            name="ck_evidence_links_module_valid",
        ),
        UniqueConstraint("evidence_id", "linked_module", "linked_record_id", name="uq_evidence_links_unique_target"),
        Index("ix_evidence_links_module_record", "linked_module", "linked_record_id"),
    )

    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence_register.id"), nullable=False, index=True)
    linked_module: Mapped[str] = mapped_column(String(50), nullable=False)
    linked_record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    evidence: Mapped[EvidenceRegister] = relationship("EvidenceRegister", back_populates="links")
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_user_id])
