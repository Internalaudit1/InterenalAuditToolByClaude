from __future__ import annotations

from app.core.enums import AttachmentOwnerType
from app.models import ActivityLog, ActionPlan, ActionPlanRevision, Attachment, Notification, RefreshToken, RiskType, User
from app.schemas.user import UserCreate
from app.services.user import user_service
from tests.conftest import TestingSessionLocal, auth_headers


def test_delete_master_record_blocked_when_referenced(client):
    auditor_headers = auth_headers(client, "auditoruser1")
    response = client.delete("/api/v1/master/countries/1", headers=auditor_headers)

    assert response.status_code == 409
    assert "referenced by active" in response.json()["detail"]


def test_auditee_cannot_delete_action_plan(client):
    auditor_headers = auth_headers(client, "auditoruser1")
    create_response = client.post(
        "/api/v1/action-plans",
        json={
            "audit_id": 1,
            "location_id": 1,
            "root_cause_id": 1,
            "observation_heading": "Delete guard test",
            "observation_grading_id": 1,
            "detailed_observation": "Testing delete permissions.",
            "risk_type_id": 1,
            "agreed_timeline": "2026-04-30",
            "auditor_status": "Pending to be initiated",
            "auditee_status": "Pending to be initiated",
            "review_quarter": "Q1",
            "responsibility_department": "Finance",
            "implementation_owner_user_id": 3,
            "assigned_auditor_user_id": 2,
        },
        headers=auditor_headers,
    )
    action_plan_id = create_response.json()["id"]

    auditee_headers = auth_headers(client, "auditeeuser1")
    response = client.delete(f"/api/v1/action-plans/{action_plan_id}", headers=auditee_headers)

    assert response.status_code == 403


def test_action_plan_delete_soft_deletes_revisions_and_attachments(client):
    auditor_headers = auth_headers(client, "auditoruser1")
    create_response = client.post(
        "/api/v1/action-plans",
        json={
            "audit_id": 1,
            "location_id": 1,
            "root_cause_id": 1,
            "observation_heading": "Delete cascade",
            "observation_grading_id": 1,
            "detailed_observation": "Testing delete cascade.",
            "risk_type_id": 1,
            "agreed_timeline": "2026-04-30",
            "auditor_status": "Pending to be initiated",
            "auditee_status": "Pending to be initiated",
            "review_quarter": "Q1",
            "responsibility_department": "Finance",
            "implementation_owner_user_id": 3,
            "assigned_auditor_user_id": 2,
        },
        headers=auditor_headers,
    )
    action_plan_id = create_response.json()["id"]

    with TestingSessionLocal() as db:
        attachment = Attachment(
            owner_type=AttachmentOwnerType.ACTION_PLAN.value,
            owner_id=action_plan_id,
            file_name="evidence.txt",
            stored_name="evidence.txt",
            content_type="text/plain",
            file_size=16,
            storage_path="storage/evidence.txt",
            uploaded_by_user_id=2,
            created_by="test",
            updated_by="test",
        )
        db.add(attachment)
        db.flush()

        revision = ActionPlanRevision(
            action_plan_id=action_plan_id,
            revision_number=1,
            management_implementation_remarks="Attached evidence",
            file_attachment_id=attachment.id,
            updated_by_user_id=2,
            status_snapshot={"auditor_status": "Pending to be initiated", "auditee_status": "Pending to be initiated"},
            created_by="test",
            updated_by="test",
        )
        db.add(revision)
        db.commit()

    delete_response = client.delete(f"/api/v1/action-plans/{action_plan_id}", headers=auditor_headers)
    assert delete_response.status_code == 200

    list_response = client.get("/api/v1/action-plans?page_size=50", headers=auditor_headers)
    ids = [item["id"] for item in list_response.json()["items"]]
    assert action_plan_id not in ids

    with TestingSessionLocal() as db:
        action_plan = db.get(ActionPlan, action_plan_id)
        assert action_plan is not None
        assert action_plan.is_deleted is True

        revisions = db.query(ActionPlanRevision).filter(ActionPlanRevision.action_plan_id == action_plan_id).all()
        assert revisions
        assert all(revision.is_deleted is True for revision in revisions)

        attachments = db.query(Attachment).filter(Attachment.owner_id == action_plan_id).all()
        assert attachments
        assert all(attachment.is_deleted is True for attachment in attachments)

        delete_log = db.query(ActivityLog).filter(ActivityLog.entity_id == str(action_plan_id), ActivityLog.action_type == "delete").one_or_none()
        assert delete_log is not None


def test_bulk_delete_returns_deleted_and_blocked_ids(client):
    auditor_headers = auth_headers(client, "auditoruser1")
    create_response = client.post(
        "/api/v1/action-plans",
        json={
            "audit_id": 1,
            "location_id": 1,
            "root_cause_id": 1,
            "observation_heading": "Bulk delete dependency",
            "observation_grading_id": 1,
            "detailed_observation": "Create a dependency for risk type delete blocking.",
            "risk_type_id": 1,
            "agreed_timeline": "2026-04-30",
            "auditor_status": "Pending to be initiated",
            "auditee_status": "Pending to be initiated",
            "review_quarter": "Q1",
            "responsibility_department": "Finance",
            "implementation_owner_user_id": 3,
            "assigned_auditor_user_id": 2,
        },
        headers=auditor_headers,
    )
    assert create_response.status_code == 200
    with TestingSessionLocal() as db:
        unreferenced = RiskType(code="NEW-RISK", name="New Risk", description="Unused", created_by="test", updated_by="test")
        db.add(unreferenced)
        db.commit()
        db.refresh(unreferenced)
        unreferenced_id = unreferenced.id

    response = client.post(
        "/api/v1/master/risk-types/bulk-delete",
        json={"ids": [1, unreferenced_id]},
        headers=auditor_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert unreferenced_id in payload["deleted_ids"]
    assert any(item["id"] == 1 for item in payload["blocked"])

    list_response = client.get("/api/v1/master/risk-types", headers=auditor_headers)
    list_ids = [item["id"] for item in list_response.json()["items"]]
    assert unreferenced_id not in list_ids


def test_user_delete_permissions_and_cleanup(client):
    auditor_headers = auth_headers(client, "auditoruser1")
    super_admin_headers = auth_headers(client, "superadmin")

    with TestingSessionLocal() as db:
        user = user_service.create_user(
            db,
            UserCreate(
                username="deletecandidate",
                email="deletecandidate@example.com",
                full_name="Delete Candidate",
                password="Password@123",
                designation_id=1,
                company_id=1,
                location_id=1,
                role_codes=["auditee"],
            ),
            "test",
        )
        db.commit()
        db.refresh(user)
        user_id = user.id

    forbidden_response = client.delete(f"/api/v1/admin/users/{user_id}", headers=auditor_headers)
    assert forbidden_response.status_code == 403

    login = client.post("/api/v1/auth/login", json={"username": "deletecandidate", "password": "Password@123"})
    assert login.status_code == 200

    with TestingSessionLocal() as db:
        notification = Notification(user_id=user_id, title="Cleanup", message="Delete me", created_by="test", updated_by="test")
        db.add(notification)
        db.commit()

    delete_response = client.delete(f"/api/v1/admin/users/{user_id}", headers=super_admin_headers)
    assert delete_response.status_code == 200

    with TestingSessionLocal() as db:
        deleted_user = db.get(User, user_id)
        assert deleted_user is not None
        assert deleted_user.is_deleted is True
        assert deleted_user.is_active is False

        refresh_tokens = db.query(RefreshToken).filter(RefreshToken.user_id == user_id).all()
        assert refresh_tokens
        assert all(token.is_deleted is True for token in refresh_tokens)
        assert all(token.revoked_at is not None for token in refresh_tokens)

        notifications = db.query(Notification).filter(Notification.user_id == user_id).all()
        assert notifications
        assert all(notification.is_deleted is True for notification in notifications)


def test_user_delete_blocked_when_user_has_assignments(client):
    super_admin_headers = auth_headers(client, "superadmin")

    response = client.delete("/api/v1/admin/users/2", headers=super_admin_headers)

    assert response.status_code == 409
    assert "still assigned" in response.json()["detail"]
