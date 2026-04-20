from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_metadata_tables_are_filtered_to_accessible_schema(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    response = client.get("/api/v1/meta/tables", headers=headers)
    payload = response.json()

    assert response.status_code == 200
    assert any(table["table_name"] == "countries" for table in payload)
    assert any(table["table_name"] == "audit_plans" for table in payload)
    assert not any(table["table_name"] == "refresh_tokens" for table in payload)


def test_metadata_columns_include_foreign_key_lookup(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    response = client.get("/api/v1/meta/tables/states/columns", headers=headers)
    payload = response.json()

    assert response.status_code == 200
    country_column = next(column for column in payload if column["name"] == "country_id")
    assert country_column["input_type"] == "select"
    assert country_column["foreign_key"]["references_table"] == "countries"
    assert country_column["lookup"]["endpoint"] == "/master/countries"


def test_metadata_rows_include_readable_foreign_key_labels(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    response = client.get("/api/v1/meta/tables/states/rows?page_size=50", headers=headers)
    payload = response.json()

    assert response.status_code == 200
    assert payload["items"][0]["country_id__label"] == "India"
    assert payload["meta"]["total"] >= 1


def test_internal_tables_are_admin_only(client: TestClient):
    auditee_headers = auth_headers(client, "auditeeuser1")
    forbidden = client.get("/api/v1/meta/tables/refresh_tokens/rows", headers=auditee_headers)
    assert forbidden.status_code == 403

    admin_headers = auth_headers(client, "superadmin")
    allowed = client.get("/api/v1/meta/tables/refresh_tokens/columns", headers=admin_headers)
    assert allowed.status_code == 200
