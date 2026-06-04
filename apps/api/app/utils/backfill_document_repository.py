from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AttachmentOwnerType
from app.db.session import SessionLocal
from app.models.action_plan import ActionPlan
from app.models.audit import Audit
from app.models.engagement import EngagementDocument, EngagementPlan
from app.models.support import Attachment
from app.models.workpaper import EvidenceRegister, Workpaper, WorkpaperVersion
from app.services.file_storage import file_storage


@dataclass
class BackfillReport:
    moved: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "moved": self.moved,
            "skipped": self.skipped,
            "missing": self.missing,
            "unresolved": self.unresolved,
        }


def _audit_segment(audit: Audit | None, audit_id: int | None = None, audit_number: str | None = None) -> str:
    reference = audit_number or (audit.audit_number if audit else None) or f"id-{audit_id or 'unknown'}"
    return f"audit-{reference}"


def _audit(db: Session, audit_id: int | None) -> Audit | None:
    if not audit_id:
        return None
    return db.scalar(select(Audit).where(Audit.id == audit_id, Audit.is_deleted.is_(False)))


def _attachment_segments(db: Session, attachment: Attachment) -> list[object] | None:
    if attachment.owner_type == AttachmentOwnerType.ACTION_PLAN.value:
        action_plan = db.scalar(
            select(ActionPlan).where(
                ActionPlan.id == attachment.owner_id,
                ActionPlan.is_deleted.is_(False),
            )
        )
        if not action_plan:
            return None
        return [
            _audit_segment(_audit(db, action_plan.audit_id), action_plan.audit_id, action_plan.audit_number),
            "action-plans",
            action_plan.action_plan_id or f"id-{action_plan.id}",
            "attachments",
        ]

    if attachment.owner_type == AttachmentOwnerType.WORKPAPER_VERSION.value:
        version = db.scalar(
            select(WorkpaperVersion).where(
                WorkpaperVersion.document_id == attachment.id,
                WorkpaperVersion.is_deleted.is_(False),
            )
        )
        if not version:
            return None
        workpaper = db.scalar(
            select(Workpaper).where(
                Workpaper.id == version.workpaper_id,
                Workpaper.is_deleted.is_(False),
            )
        )
        if not workpaper:
            return None
        return [
            _audit_segment(_audit(db, workpaper.audit_id), workpaper.audit_id),
            "workpapers",
            workpaper.workpaper_code or f"id-{workpaper.id}",
            f"version-{version.version_no:03d}",
        ]

    if attachment.owner_type == AttachmentOwnerType.EVIDENCE_REGISTER.value:
        evidence = db.scalar(
            select(EvidenceRegister).where(
                EvidenceRegister.document_id == attachment.id,
                EvidenceRegister.is_deleted.is_(False),
            )
        )
        if not evidence:
            return None
        return [
            _audit_segment(_audit(db, evidence.audit_id), evidence.audit_id),
            "evidence",
            evidence.evidence_code or f"id-{evidence.id}",
        ]

    if attachment.owner_type == "engagement_plan":
        document = db.scalar(
            select(EngagementDocument).where(
                EngagementDocument.document_id == attachment.id,
                EngagementDocument.is_deleted.is_(False),
            )
        )
        if not document:
            return None
        plan = db.scalar(
            select(EngagementPlan).where(
                EngagementPlan.id == document.engagement_plan_id,
                EngagementPlan.is_deleted.is_(False),
            )
        )
        if not plan:
            return None
        return [
            _audit_segment(_audit(db, plan.audit_id), plan.audit_id),
            "engagement-plans",
            plan.engagement_code or f"id-{plan.id}",
            document.document_type,
        ]

    return None


def backfill_document_repository(db: Session, *, apply: bool = False) -> BackfillReport:
    report = BackfillReport()
    attachments = db.scalars(select(Attachment).where(Attachment.is_deleted.is_(False)).order_by(Attachment.id)).all()
    for attachment in attachments:
        label = f"attachment#{attachment.id}:{attachment.file_name}"
        source = Path(attachment.storage_path)
        if not source.exists():
            report.missing.append(label)
            continue

        segments = _attachment_segments(db, attachment)
        if not segments:
            report.unresolved.append(label)
            continue

        target = (
            file_storage.root
            / file_storage.relative_dir(*segments)
            / file_storage.safe_segment(attachment.stored_name, fallback=source.name)
        ).resolve()
        if source.resolve() == target:
            report.skipped.append(label)
            continue

        if apply:
            new_path = file_storage.move_to_context(str(source), *segments, stored_name=attachment.stored_name)
            attachment.storage_path = new_path
            attachment.updated_by = "document_repository_backfill"
            report.moved.append(f"{label} -> {new_path}")
        else:
            report.moved.append(f"{label} -> {target}")

    if apply:
        db.commit()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill attachments into the structured local document repository.")
    parser.add_argument("--apply", action="store_true", help="Move files and update attachment storage paths. Without this flag, runs as a dry run.")
    args = parser.parse_args()
    with SessionLocal() as db:
        report = backfill_document_repository(db, apply=args.apply)
    for key, values in report.as_dict().items():
        print(f"{key}: {len(values)}")
        for value in values:
            print(f"  - {value}")


if __name__ == "__main__":
    main()
