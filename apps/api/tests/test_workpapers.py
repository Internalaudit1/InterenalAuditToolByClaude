from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AuditMembershipRole
from app.models.audit import Audit, AuditMembership
from app.services.user import user_service

from .conftest import auth_headers


def ensure_audit_membership(db: Session) -> None:
    audit = db.scalar(select(Audit).where(Audit.id == 1))
    auditor = user_service.get_by_username(db, "auditoruser1")
    if not audit or not auditor:
        return
    existing = db.scalar(
        select(AuditMembership).where(
            AuditMembership.audit_id == audit.id,
            AuditMembership.user_id == auditor.id,
            AuditMembership.role_on_audit == AuditMembershipRole.LEAD_AUDITOR.value,
        )
    )
    if existing:
        return
    db.add(
        AuditMembership(
            audit_id=audit.id,
            user_id=auditor.id,
            role_on_audit=AuditMembershipRole.LEAD_AUDITOR.value,
            created_by="test",
            updated_by="test",
        )
    )
    db.commit()


def test_workpaper_workflow_and_evidence_linking(client, setup_database: Session):
    ensure_audit_membership(setup_database)
    auditor_headers = auth_headers(client, "auditoruser1")
    super_headers = auth_headers(client, "superadmin")

    create_response = client.post(
        "/api/v1/workpapers",
        headers=auditor_headers,
        json={
            "audit_id": 1,
            "title": "Cash Count Workpaper",
            "folder_path": "/Fieldwork/Cash",
            "owner_user_id": 2,
            "reviewer_user_id": 1,
        },
    )
    assert create_response.status_code == 200, create_response.text
    workpaper = create_response.json()
    assert workpaper["status"] == "Draft"
    assert workpaper["workpaper_code"].startswith("WP-")

    upload_response = client.post(
        f"/api/v1/workpapers/{workpaper['id']}/versions",
        headers=auditor_headers,
        files={"file": ("cash-count.txt", b"count-sheet-v1", "text/csv")},
        data={"change_summary": "Initial walkthrough evidence pack."},
    )
    assert upload_response.status_code == 200, upload_response.text
    uploaded = upload_response.json()
    assert uploaded["current_version_no"] == 1
    assert len(uploaded["versions"]) == 1

    submit_response = client.post(
        f"/api/v1/workpapers/{workpaper['id']}/submit-review",
        headers=auditor_headers,
        json={"comment": "Ready for reviewer sign-off."},
    )
    assert submit_response.status_code == 200, submit_response.text
    assert submit_response.json()["status"] == "Submitted for Review"

    reviewed_response = client.post(
        f"/api/v1/workpapers/{workpaper['id']}/review",
        headers=super_headers,
        json={"review_status": "Reviewed", "review_comment": "Structure reviewed."},
    )
    assert reviewed_response.status_code == 200, reviewed_response.text
    assert reviewed_response.json()["status"] == "Reviewed"

    approved_response = client.post(
        f"/api/v1/workpapers/{workpaper['id']}/review",
        headers=super_headers,
        json={"review_status": "Approved", "review_comment": "Approved for reliance."},
    )
    assert approved_response.status_code == 200, approved_response.text
    assert approved_response.json()["status"] == "Approved"

    locked_response = client.post(
        f"/api/v1/workpapers/{workpaper['id']}/review",
        headers=super_headers,
        json={"review_status": "Locked", "review_comment": "Final lock after sign-off."},
    )
    assert locked_response.status_code == 200, locked_response.text
    assert locked_response.json()["status"] == "Locked"
    assert locked_response.json()["signoff_at"] is not None
    assert len(locked_response.json()["reviews"]) == 3

    observation_response = client.post(
        "/api/v1/audits/1/observations",
        headers=auditor_headers,
        json={
            "heading": "Cash variance not investigated",
            "observation_text": "Differences between the ledger and cash count were not investigated promptly.",
            "observation_grading_id": 1,
            "risk_type_id": 1,
            "auditee_user_id": 3,
        },
    )
    assert observation_response.status_code == 200, observation_response.text
    observation_id = observation_response.json()["id"]

    evidence_response = client.post(
        "/api/v1/evidence",
        headers=auditor_headers,
        files={"file": ("cash-support.csv", b"voucher-id,amount\n1,2500", "text/csv")},
        data={
            "audit_id": "1",
            "source_type": "Walkthrough",
            "source_name": "Cash Count Sheet",
            "evidence_description": "Supporting cash count working file.",
            "confidentiality_level": "Confidential",
        },
    )
    assert evidence_response.status_code == 200, evidence_response.text
    evidence = evidence_response.json()
    assert evidence["evidence_code"].startswith("EVR-")

    link_workpaper_response = client.post(
        f"/api/v1/evidence/{evidence['id']}/link",
        headers=auditor_headers,
        json={"linked_module": "workpaper", "linked_record_id": workpaper["id"]},
    )
    assert link_workpaper_response.status_code == 200, link_workpaper_response.text
    assert len(link_workpaper_response.json()["links"]) == 1

    link_observation_response = client.post(
        f"/api/v1/evidence/{evidence['id']}/link",
        headers=auditor_headers,
        json={"linked_module": "observation", "linked_record_id": observation_id},
    )
    assert link_observation_response.status_code == 200, link_observation_response.text
    assert len(link_observation_response.json()["links"]) == 2

    detail_response = client.get(f"/api/v1/workpapers/{workpaper['id']}", headers=auditor_headers)
    assert detail_response.status_code == 200, detail_response.text
    assert evidence["id"] in detail_response.json()["linked_evidence_ids"]
