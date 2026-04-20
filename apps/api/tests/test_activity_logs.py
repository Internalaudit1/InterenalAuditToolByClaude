from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_activity_log_created_for_login_and_visible_to_super_admin(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "auditoruser1", "password": "Password@123"})
    headers = auth_headers(client, "superadmin")
    response = client.get("/api/v1/admin/activity-logs", headers=headers)
    assert response.status_code == 200
    assert any(item["module"] == "auth" and item["action_type"] == "login" for item in response.json()["items"])
