from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_reports_filter_by_status(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    response = client.get("/api/v1/reports?status=In%20Progress", headers=headers)
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert rows
    assert all(row["status"] == "In Progress" for row in rows)

