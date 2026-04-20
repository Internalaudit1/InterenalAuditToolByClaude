from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_login_success(client: TestClient):
    response = client.post("/api/v1/auth/login", json={"username": "auditoruser1", "password": "Password@123"})
    payload = response.json()
    assert response.status_code == 200
    assert payload["user"]["roles"] == ["auditor"]
    assert payload["access_token"]


def test_refresh_token_success(client: TestClient):
    login = client.post("/api/v1/auth/login", json={"username": "superadmin", "password": "Password@123"})
    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": login.json()["refresh_token"]})
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]


def test_invalid_access_token_returns_401(client: TestClient):
    response = client.get("/api/v1/planning/process-risk-mappings", headers={"Authorization": "Bearer definitely-invalid"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Access token is invalid."
