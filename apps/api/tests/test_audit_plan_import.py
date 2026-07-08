from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from .conftest import auth_headers

HEADERS = ["S. No.", "Audit Area", "Audit Name", "Company", "Location", "Fiscal Year", "Criticality", "CARO/Non-CARO", "Internal/External"]
API = "/api/v1/imports/audit-plans"


def _xlsx(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(HEADERS)
    for r in rows:
        ws.append(r)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _file(content: bytes):
    return {"file": ("plan.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}


def test_validate_flags_bad_rows_and_blocks_commit(client, setup_database):
    head = auth_headers(client, "superadmin")
    content = _xlsx([
        [1, "Procurement", "Procurement Review", "NHL Limited", "002", "2026-2027", "High", "CARO", "Internal"],
        [2, "Payroll", "Payroll Review", "Unknown Co", "002", "2026-2027", "Medium", "CARO", "Internal"],
    ])
    resp = client.post(f"{API}/validate", headers=head, files=_file(content))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_rows"] == 2
    assert body["valid_rows"] == 1
    assert body["invalid_rows"] == 1
    assert body["can_commit"] is False
    # strict fixed-format: commit blocked, nothing saved
    commit = client.post(f"{API}/commit", headers=head, files=_file(content))
    assert commit.status_code == 422, commit.text
    assert commit.json()["imported_rows"] == 0


def test_commit_creates_draft_plans(client, setup_database):
    head = auth_headers(client, "superadmin")
    content = _xlsx([
        [1, "Procurement", "Procurement Review", "NHL Limited", "002", "2026-2027", "High", "CARO", "Internal"],
        [2, "Treasury", "Treasury Review", "NHL Limited", "Bengaluru Shared Services", "2026-2027", "Medium", "Non-CARO", "External"],
    ])
    commit = client.post(f"{API}/commit", headers=head, files=_file(content))
    assert commit.status_code == 200, commit.text
    assert commit.json()["imported_rows"] == 2

    plans = client.get("/api/v1/planning/audit-plans?page_size=100", headers=head).json()["items"]
    imported = [p for p in plans if p.get("audit_area") in {"Procurement", "Treasury"}]
    assert len(imported) == 2
    for plan in imported:
        assert plan["approval_status"] == "Draft"
        assert plan["audit_number"].startswith("AUD-")
        assert plan["caro_status"] in {"CARO", "Non-CARO"}


def test_missing_required_column_rejected(client, setup_database):
    head = auth_headers(client, "superadmin")
    wb = Workbook()
    ws = wb.active
    ws.append(["S. No.", "Audit Area", "Company"])  # missing Audit Name / Location / Fiscal Year
    ws.append([1, "Procurement", "NHL Limited"])
    buf = BytesIO(); wb.save(buf)
    resp = client.post(f"{API}/validate", headers=head, files=_file(buf.getvalue()))
    assert resp.status_code == 422, resp.text


def test_auditee_cannot_import_plans(client, setup_database):
    auditee = auth_headers(client, "auditeeuser1")
    content = _xlsx([[1, "Procurement", "Procurement Review", "NHL Limited", "002", "2026-2027", "High", "CARO", "Internal"]])
    resp = client.post(f"{API}/validate", headers=auditee, files=_file(content))
    assert resp.status_code == 403, resp.text
