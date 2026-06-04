from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from tests.conftest import auth_headers

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def workbook_bytes(headers: list[str], rows: list[list[object]], sheet_name: str = "Data_Entry") -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def upload(client: TestClient, path: str, headers: dict[str, str], content: bytes, filename: str = "import.xlsx"):
    return client.post(path, headers=headers, files={"file": (filename, content, XLSX_MEDIA_TYPE)})


def test_template_generation_for_states_includes_reference_values(client: TestClient):
    headers = auth_headers(client, "auditoruser1")

    response = client.get("/api/v1/imports/master/states/template", headers=headers)

    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content))
    assert "Data_Entry" in workbook.sheetnames
    assert "Instructions" in workbook.sheetnames
    assert "Reference_Values" in workbook.sheetnames
    assert [cell.value for cell in workbook["Data_Entry"][1]][:5] == ["country_code", "code", "name", "description", "is_active"]
    assert workbook["Reference_Values"]["A1"].value == "country_code"
    assert workbook["Reference_Values"]["A2"].value == "IN"


def test_validate_rejects_wrong_headers(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    content = workbook_bytes(["wrong_code", "name"], [["JP", "Japan"]])

    response = upload(client, "/api/v1/imports/master/countries/validate", headers, content)
    payload = response.json()

    assert response.status_code == 200
    assert payload["can_commit"] is False
    assert any(error["message"] == "Missing required header(s)." for error in payload["errors"])
    assert any(error["message"] == "Unexpected header(s) found." for error in payload["errors"])


def test_validate_detects_required_fields_and_duplicates_inside_file(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    content = workbook_bytes(
        ["code", "name", "description", "is_active"],
        [
            ["JP", "Japan", "Japan country", "TRUE"],
            ["JP", "Japan Duplicate", "Duplicate code", "TRUE"],
            ["", "Missing Code", "", "TRUE"],
        ],
    )

    response = upload(client, "/api/v1/imports/master/countries/validate", headers, content)
    payload = response.json()

    assert response.status_code == 200
    assert payload["total_rows"] == 3
    assert payload["valid_rows"] == 0
    assert payload["invalid_rows"] == 3
    assert any("appears multiple times" in error["message"] for error in payload["errors"])
    assert any(error["field"] == "code" and error["message"] == "code is required." for error in payload["errors"])


def test_validate_detects_duplicate_against_database(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    content = workbook_bytes(["code", "name", "description", "is_active"], [["IN", "India Copy", "", "TRUE"]])

    response = upload(client, "/api/v1/imports/master/countries/validate", headers, content)
    payload = response.json()

    assert response.status_code == 200
    assert payload["can_commit"] is False
    assert any("already exists" in error["message"] for error in payload["errors"])


def test_validate_resolves_state_and_city_foreign_keys(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    state_content = workbook_bytes(
        ["country_code", "code", "name", "description", "is_active"],
        [["IN", "DL", "Delhi", "", "TRUE"], ["XX", "ZZ", "Invalid", "", "TRUE"]],
    )
    city_content = workbook_bytes(
        ["state_code", "code", "name", "description", "is_active"],
        [["KA", "MYS", "Mysuru", "", "TRUE"], ["NOPE", "BAD", "Invalid", "", "TRUE"]],
    )

    state_response = upload(client, "/api/v1/imports/master/states/validate", headers, state_content)
    city_response = upload(client, "/api/v1/imports/master/cities/validate", headers, city_content)

    assert state_response.status_code == 200
    assert state_response.json()["valid_rows"] == 1
    assert any("Country with code 'XX' was not found" in error["message"] for error in state_response.json()["errors"])
    assert city_response.status_code == 200
    assert city_response.json()["valid_rows"] == 1
    assert any("State with code 'NOPE' was not found" in error["message"] for error in city_response.json()["errors"])


def test_template_generation_for_linked_location_master(client: TestClient):
    headers = auth_headers(client, "auditoruser1")

    response = client.get("/api/v1/imports/master/locations/template", headers=headers)

    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content))
    assert "Reference_Values" in workbook.sheetnames
    assert [cell.value for cell in workbook["Data_Entry"][1]][:8] == [
        "sector",
        "division_id",
        "division_description",
        "country_code",
        "state_code",
        "city_code",
        "company_name",
        "location_code",
    ]


def test_validate_company_import_rejects_invalid_geography_chain(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    country = client.post("/api/v1/master/countries", headers=headers, json={"code": "UK", "name": "United Kingdom"}).json()
    state = client.post("/api/v1/master/states", headers=headers, json={"country_id": country["id"], "code": "LDN", "name": "London"}).json()
    client.post("/api/v1/master/cities", headers=headers, json={"state_id": state["id"], "code": "LON", "name": "London"})
    content = workbook_bytes(
        ["name", "country_code", "state_code", "city_code", "pan", "gst_no", "is_active"],
        [["Mismatch Ltd", "IN", "LDN", "LON", "AAACM1234Q", "29AAACM1234Q1Z2", "TRUE"]],
    )

    response = upload(client, "/api/v1/imports/master/companies/validate", headers, content)
    payload = response.json()

    assert response.status_code == 200
    assert payload["can_commit"] is False
    assert any("Selected state does not belong to the selected country." in error["message"] for error in payload["errors"])


def test_commit_imports_linked_trial_balance(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    content = workbook_bytes(
        ["code", "name", "company_name", "amount", "is_active"],
        [["TB-2026", "FY 2026 Trial Balance", "NHL Limited", 12500.75, "TRUE"]],
    )

    response = upload(client, "/api/v1/imports/master/trial-balances/commit", headers, content)
    payload = response.json()

    assert response.status_code == 200
    assert payload["imported_rows"] == 1
    list_response = client.get("/api/v1/master/trial-balances?search=TB-2026", headers=headers)
    assert list_response.status_code == 200
    assert any(item["code"] == "TB-2026" for item in list_response.json()["items"])


def test_validate_task_swap_rejects_same_source_and_target(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    content = workbook_bytes(
        ["code", "source_designation_code", "target_designation_code", "max_tasks", "notes", "is_active"],
        [["SWAP-SELF", "AUD", "AUD", 5, "Invalid self swap", "TRUE"]],
    )

    response = upload(client, "/api/v1/imports/master/task-swaps/validate", headers, content)
    payload = response.json()

    assert response.status_code == 200
    assert payload["can_commit"] is False
    assert any("Source and target designation must be different." in error["message"] for error in payload["errors"])


def test_commit_imports_valid_country_and_rejects_invalid_commit(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    valid_content = workbook_bytes(["code", "name", "description", "is_active"], [["JP", "Japan", "Japan country", "FALSE"]])
    invalid_content = workbook_bytes(["code", "name", "description", "is_active"], [["IN", "India Copy", "", "TRUE"]])

    invalid_response = upload(client, "/api/v1/imports/master/countries/commit", headers, invalid_content)
    assert invalid_response.status_code == 422
    assert invalid_response.json()["imported_rows"] == 0

    response = upload(client, "/api/v1/imports/master/countries/commit", headers, valid_content)
    payload = response.json()

    assert response.status_code == 200
    assert payload["imported_rows"] == 1
    list_response = client.get("/api/v1/master/countries?search=Japan", headers=headers)
    assert list_response.status_code == 200
    assert any(item["code"] == "JP" and item["is_active"] is False for item in list_response.json()["items"])


def test_error_report_downloads_xlsx_for_invalid_rows(client: TestClient):
    headers = auth_headers(client, "auditoruser1")
    content = workbook_bytes(["code", "name", "description", "is_active"], [["IN", "India Copy", "", "TRUE"]])

    response = upload(client, "/api/v1/imports/master/countries/error-report", headers, content)

    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content))
    worksheet = workbook["Import_Errors"]
    assert worksheet["E1"].value == "error_fields"
    assert "already exists" in worksheet["F2"].value


def test_auditee_cannot_import_master_data(client: TestClient):
    headers = auth_headers(client, "auditeeuser1")
    content = workbook_bytes(["code", "name", "description", "is_active"], [["JP", "Japan", "", "TRUE"]])

    validate_response = upload(client, "/api/v1/imports/master/countries/validate", headers, content)
    template_response = client.get("/api/v1/imports/master/countries/template", headers=headers)

    assert validate_response.status_code == 403
    assert template_response.status_code == 403
