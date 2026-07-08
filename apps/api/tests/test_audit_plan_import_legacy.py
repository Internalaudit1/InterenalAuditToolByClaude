from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from .conftest import auth_headers

API = "/api/v1/imports/audit-plans/legacy"

LEGACY_HEADERS = [
    "S. No.", "Audit Area", "Audit Name / Unit Name", "Period", "Executor", "Mentor",
    "Audit SPOC", "Audit Commencement Date ", "Qtr", "Audit Program  Date", "IDR Date",
    "Audit Fieldwork completed ", "Audit Fieldwork expected t", "Tentative Target Date for ",
    "Target Date for Release of", "Current Audit Status ", "Remarks",
]


def _legacy_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append([""] * len(LEGACY_HEADERS))  # blank first row like the real file
    ws.append(LEGACY_HEADERS)
    ws.append([1, "Treasury", "Treasury", "2026-03-01", "Ravi", "Rohan", "Harish", "2026-04-20", "Q1", "", "", "", "", "", "", "WIP", ""])
    ws.append([2, "Procurement", "North Plant", "2026-04-01", "Sajal", "Rohan", "PwC", "2026-05-20", "Q2", "", "", "", "", "", "", "", "urgent"])
    buf = BytesIO(); wb.save(buf)
    return buf.getvalue()


def _file():
    return {"file": ("legacy.xlsx", _legacy_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}


def test_legacy_validate_and_commit(client, setup_database):
    head = auth_headers(client, "superadmin")
    form = {"company_id": "1", "location_id": "1", "fiscal_year": "2026-2027"}

    v = client.post(f"{API}/validate", headers=head, data=form, files=_file())
    assert v.status_code == 200, v.text
    body = v.json()
    assert body["total_rows"] == 2
    assert body["valid_rows"] == 2
    assert body["can_commit"] is True

    c = client.post(f"{API}/commit", headers=head, data=form, files=_file())
    assert c.status_code == 200, c.text
    assert c.json()["imported_rows"] == 2

    plans = client.get("/api/v1/planning/audit-plans?page_size=100", headers=head).json()["items"]
    treasury = [p for p in plans if p.get("audit_area") == "Treasury"]
    assert treasury, "Treasury plan should be created"
    plan = treasury[0]
    assert plan["approval_status"] == "Draft"
    assert plan["fiscal_year"] == "2026-2027"
    assert plan["audit_number"].startswith("AUD-")
    assert "Executor: Ravi" in (plan.get("remarks") or "")
    assert "Mentor: Rohan" in (plan.get("remarks") or "")


def test_legacy_bad_company_blocks(client, setup_database):
    head = auth_headers(client, "superadmin")
    form = {"company_id": "999", "location_id": "1", "fiscal_year": "2026-2027"}
    v = client.post(f"{API}/validate", headers=head, data=form, files=_file())
    assert v.status_code == 200, v.text
    assert v.json()["can_commit"] is False
    c = client.post(f"{API}/commit", headers=head, data=form, files=_file())
    assert c.status_code == 422, c.text


def test_legacy_requires_planning_manage(client, setup_database):
    auditee = auth_headers(client, "auditeeuser1")
    form = {"company_id": "1", "location_id": "1", "fiscal_year": "2026-2027"}
    v = client.post(f"{API}/validate", headers=auditee, data=form, files=_file())
    assert v.status_code == 403, v.text
