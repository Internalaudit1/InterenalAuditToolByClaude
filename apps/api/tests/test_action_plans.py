from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_action_plan_lifecycle(client: TestClient):
    auditor_headers = auth_headers(client, "auditoruser1")
    admin_headers = auth_headers(client, "superadmin")
    create_response = client.post(
        "/api/v1/action-plans",
        json={
            "audit_id": 1,
            "location_id": 1,
            "root_cause_id": 1,
            "observation_heading": "Discount override gap",
            "observation_grading_id": 1,
            "detailed_observation": "Discounts above threshold bypass approval.",
            "risk_type_id": 1,
            "agreed_timeline": "2026-04-30",
            "auditor_status": "Pending to be initiated",
            "auditee_status": "Pending to be initiated",
            "review_quarter": "Q1",
            "responsibility_department": "Finance",
            "implementation_owner_user_id": 3,
            "assigned_auditor_user_id": 2
        },
        headers=auditor_headers,
    )
    assert create_response.status_code == 200
    assert create_response.json()["action_plan_id"].startswith("ACT-")
    assert create_response.json()["observation_number"].startswith("OBS-")
    assert create_response.json()["audit_number"].startswith("AUD-")
    action_plan_id = create_response.json()["id"]

    respond_response = client.post(
        f"/api/v1/action-plans/{action_plan_id}/response",
        json={
            "management_response": "We are configuring approval rules.",
            "agreed_action_plan": "Enable maker checker in ERP.",
            "management_implementation_remarks": "Configuration in progress.",
            "auditee_status": "In Progress",
            "revised_date": "2026-04-20",
            "attachment_ids": []
        },
        headers=admin_headers,
    )
    assert respond_response.status_code == 200
    assert respond_response.json()["auditee_status"] == "In Progress"

    invalid_complete = client.post(
        f"/api/v1/action-plans/{action_plan_id}/review",
        json={"auditor_status": "Completed", "auditor_implementation_remarks": "Trying to complete too early"},
        headers=auditor_headers,
    )
    assert invalid_complete.status_code == 422

    move_under_review = client.post(
        f"/api/v1/action-plans/{action_plan_id}/response",
        json={
            "management_response": "Evidence attached",
            "agreed_action_plan": "Enable maker checker in ERP.",
            "management_implementation_remarks": "Ready for review.",
            "auditee_status": "Under Review",
            "revised_date": "2026-04-21",
            "attachment_ids": []
        },
        headers=admin_headers,
    )
    assert move_under_review.status_code == 200

    complete_response = client.post(
        f"/api/v1/action-plans/{action_plan_id}/review",
        json={"auditor_status": "Completed", "auditor_implementation_remarks": "Validated closure evidence."},
        headers=auditor_headers,
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["auditor_status"] == "Completed"


def test_auditee_cannot_set_auditor_status_directly(client: TestClient):
    auditor_headers = auth_headers(client, "auditoruser1")
    create_response = client.post(
        "/api/v1/action-plans",
        json={
            "audit_id": 1,
            "location_id": 1,
            "root_cause_id": 1,
            "observation_heading": "Review evidence gap",
            "observation_grading_id": 1,
            "detailed_observation": "Missing sign-off archive.",
            "risk_type_id": 1,
            "agreed_timeline": "2026-04-30",
            "auditor_status": "Pending to be initiated",
            "auditee_status": "Pending to be initiated",
            "review_quarter": "Q1",
            "responsibility_department": "Finance",
            "implementation_owner_user_id": 3,
            "assigned_auditor_user_id": 2
        },
        headers=auditor_headers,
    )
    action_plan_id = create_response.json()["id"]
    auditee_headers = auth_headers(client, "auditeeuser1")
    response = client.post(
        f"/api/v1/action-plans/{action_plan_id}/review",
        json={"auditor_status": "Completed", "auditor_implementation_remarks": "Not allowed"},
        headers=auditee_headers,
    )
    assert response.status_code == 403


def test_auditee_can_update_only_implementation_remarks(client: TestClient):
    auditor_headers = auth_headers(client, "auditoruser1")
    create_response = client.post(
        "/api/v1/action-plans",
        json={
            "audit_id": 1,
            "location_id": 1,
            "root_cause_id": 1,
            "observation_heading": "Implementation note gap",
            "observation_grading_id": 1,
            "detailed_observation": "Implementation status is not documented.",
            "risk_type_id": 1,
            "agreed_timeline": "2026-04-30",
            "auditor_status": "Pending to be initiated",
            "auditee_status": "Pending to be initiated",
            "review_quarter": "Q1",
            "responsibility_department": "Finance",
            "implementation_owner_user_id": 3,
            "assigned_auditor_user_id": 2,
            "management_response": "Original management response",
            "agreed_action_plan": "Original action plan"
        },
        headers=auditor_headers,
    )
    assert create_response.status_code == 200
    action_plan_id = create_response.json()["id"]
    original_revision_count = create_response.json()["revision_count"]
    auditee_headers = auth_headers(client, "auditeeuser1")

    broad_response = client.post(
        f"/api/v1/action-plans/{action_plan_id}/response",
        json={
            "management_response": "Should not change",
            "agreed_action_plan": "Should not change",
            "management_implementation_remarks": "Trying broad response",
            "auditee_status": "In Progress",
            "revised_date": "2026-04-20",
            "attachment_ids": []
        },
        headers=auditee_headers,
    )
    assert broad_response.status_code == 403

    remarks_response = client.post(
        f"/api/v1/action-plans/{action_plan_id}/remarks",
        json={
            "management_implementation_remarks": "Implementation remarks updated by auditee.",
            "auditee_status": "Completed",
            "management_response": "Should be ignored"
        },
        headers=auditee_headers,
    )
    payload = remarks_response.json()

    assert remarks_response.status_code == 200
    assert payload["management_implementation_remarks"] == "Implementation remarks updated by auditee."
    assert payload["management_response"] == "Original management response"
    assert payload["agreed_action_plan"] == "Original action plan"
    assert payload["auditee_status"] == "Pending to be initiated"
    assert payload["auditor_status"] == "Pending to be initiated"
    assert payload["revision_count"] == original_revision_count + 1


def test_auditee_cannot_delete_action_plan(client: TestClient):
    auditor_headers = auth_headers(client, "auditoruser1")
    create_response = client.post(
        "/api/v1/action-plans",
        json={
            "audit_id": 1,
            "location_id": 1,
            "root_cause_id": 1,
            "observation_heading": "Delete restriction check",
            "observation_grading_id": 1,
            "detailed_observation": "Auditee should not delete this record.",
            "risk_type_id": 1,
            "agreed_timeline": "2026-04-30",
            "auditor_status": "Pending to be initiated",
            "auditee_status": "Pending to be initiated",
            "review_quarter": "Q1",
            "responsibility_department": "Finance",
            "implementation_owner_user_id": 3,
            "assigned_auditor_user_id": 2
        },
        headers=auditor_headers,
    )
    action_plan_id = create_response.json()["id"]
    auditee_headers = auth_headers(client, "auditeeuser1")

    delete_response = client.delete(f"/api/v1/action-plans/{action_plan_id}", headers=auditee_headers)

    assert delete_response.status_code == 403
