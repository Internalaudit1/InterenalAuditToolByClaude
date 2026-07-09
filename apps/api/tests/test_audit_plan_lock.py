from __future__ import annotations

from datetime import date, timedelta

from .conftest import auth_headers

API = "/api/v1/planning"


def _approved_plan(client, headers) -> int:
    start = date.today().isoformat()
    end = (date.today() + timedelta(days=30)).isoformat()
    plan_id = client.post(
        f"{API}/audit-plans",
        headers=headers,
        json={
            "audit_name": "Payroll FY27",
            "company_id": 1,
            "location_id": 1,
            "period_type": "Quarterly",
            "period_value": "Q1",
            "fiscal_year": "2026-2027",
            "start_date": start,
            "end_date": end,
            "criticality": "High",
            "audit_area": "Payroll",
            "caro_status": "CARO",
            "audit_scope_type": "Internal",
        },
    ).json()["id"]
    assert client.post(f"{API}/audit-plans/{plan_id}/submit-for-approval", headers=headers).status_code == 200
    assert client.post(f"{API}/audit-plans/{plan_id}/approve", headers=headers).status_code == 200
    return plan_id


def test_approved_plan_rejects_non_remarks_update(client, setup_database):
    head = auth_headers(client, "superadmin")
    plan_id = _approved_plan(client, head)
    resp = client.put(f"{API}/audit-plans/{plan_id}", headers=head, json={"audit_name": "Renamed After Approval"})
    assert resp.status_code == 422, resp.text
    assert "locked" in resp.text.lower()


def test_approved_plan_allows_remarks_update(client, setup_database):
    head = auth_headers(client, "superadmin")
    plan_id = _approved_plan(client, head)
    resp = client.put(f"{API}/audit-plans/{plan_id}", headers=head, json={"remarks": "Reviewed and noted."})
    assert resp.status_code == 200, resp.text
    assert resp.json()["remarks"] == "Reviewed and noted."
