from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _create_user(client: TestClient, headers: dict[str, str], *, username: str, role_codes: list[str]):
    return client.post(
        "/api/v1/admin/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "full_name": username.replace("_", " ").title(),
            "password": "Password@123",
            "designation_id": 1,
            "company_id": 1,
            "location_id": 1,
            "role_codes": role_codes,
        },
        headers=headers,
    )


def _create_action_plan(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/action-plans",
        json={
            "audit_id": 1,
            "location_id": 1,
            "root_cause_id": 1,
            "observation_heading": "Management review test",
            "observation_grading_id": 1,
            "detailed_observation": "Management should add review notes without changing status.",
            "risk_type_id": 1,
            "agreed_timeline": "2026-04-30",
            "auditor_status": "Pending to be initiated",
            "auditee_status": "Pending to be initiated",
            "review_quarter": "Q1",
            "responsibility_department": "Finance",
            "implementation_owner_user_id": 3,
            "assigned_auditor_user_id": 2,
        },
        headers=headers,
    )
    assert response.status_code == 200
    return int(response.json()["id"])


def test_super_admin_can_manage_custom_roles(client: TestClient):
    headers = auth_headers(client, "superadmin")

    create_response = client.post(
        "/api/v1/admin/roles",
        json={"code": "custom_reviewer", "name": "Custom Reviewer", "permission_codes": ["reports:view"]},
        headers=headers,
    )
    assert create_response.status_code == 200
    role_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/v1/admin/roles/{role_id}/permissions",
        json={"permission_codes": ["reports:view", "library:view"]},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert set(update_response.json()["permission_codes"]) == {"reports:view", "library:view"}

    delete_response = client.delete(f"/api/v1/admin/roles/{role_id}", headers=headers)
    assert delete_response.status_code == 200


def test_super_admin_cannot_delete_system_role(client: TestClient):
    headers = auth_headers(client, "superadmin")
    roles = client.get("/api/v1/admin/roles", headers=headers).json()
    auditor_role = next(role for role in roles if role["code"] == "auditor")

    response = client.delete(f"/api/v1/admin/roles/{auditor_role['id']}", headers=headers)

    assert response.status_code == 409


def test_head_auditor_can_manage_users_but_not_assign_super_admin(client: TestClient):
    admin_headers = auth_headers(client, "superadmin")
    assert _create_user(client, admin_headers, username="head_auditor_test", role_codes=["head_auditor"]).status_code == 200
    head_headers = auth_headers(client, "head_auditor_test")

    allowed_response = _create_user(client, head_headers, username="head_created_auditor", role_codes=["auditor"])
    blocked_response = _create_user(client, head_headers, username="head_created_admin", role_codes=["super_admin"])

    assert allowed_response.status_code == 200
    assert blocked_response.status_code == 403


def test_management_can_create_review_notes_but_not_change_action_plan_status(client: TestClient):
    admin_headers = auth_headers(client, "superadmin")
    auditor_headers = auth_headers(client, "auditoruser1")
    assert _create_user(client, admin_headers, username="management_test", role_codes=["management"]).status_code == 200
    management_headers = auth_headers(client, "management_test")
    action_plan_id = _create_action_plan(client, auditor_headers)

    review_response = client.post(
        f"/api/v1/action-plans/{action_plan_id}/management-reviews",
        json={"review_note": "Escalate this observation to the quarterly steering committee.", "review_decision": "Escalated"},
        headers=management_headers,
    )
    status_response = client.post(
        f"/api/v1/action-plans/{action_plan_id}/review",
        json={"auditor_status": "Completed", "auditor_implementation_remarks": "Management cannot do this."},
        headers=management_headers,
    )

    assert review_response.status_code == 200
    assert review_response.json()["review_decision"] == "Escalated"
    assert status_response.status_code == 403
