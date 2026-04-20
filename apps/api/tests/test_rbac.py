from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_auditee_cannot_create_action_plan(client: TestClient):
    headers = auth_headers(client, "auditeeuser1")
    response = client.post(
        "/api/v1/action-plans",
        json={
            "audit_id": 1,
            "location_id": 1,
            "root_cause_id": 1,
            "observation_heading": "Test issue",
            "observation_grading_id": 1,
            "detailed_observation": "Long enough observation detail",
            "risk_type_id": 1,
            "agreed_timeline": "2026-04-30",
            "auditor_status": "Pending to be initiated",
            "auditee_status": "Pending to be initiated",
            "review_quarter": "Q1",
            "responsibility_department": "Finance",
            "implementation_owner_user_id": 3,
            "assigned_auditor_user_id": 2
        },
        headers=headers,
    )
    assert response.status_code == 403


def test_auditee_cannot_access_dashboard_summary(client: TestClient):
    headers = auth_headers(client, "auditeeuser1")
    response = client.get("/api/v1/dashboard/summary", headers=headers)
    assert response.status_code == 403
