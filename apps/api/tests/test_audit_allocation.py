from __future__ import annotations

from datetime import date, timedelta

from .conftest import auth_headers

API = "/api/v1/planning"


def _create_approved_plan(client, headers) -> int:
    start = date.today().isoformat()
    end = (date.today() + timedelta(days=30)).isoformat()
    resp = client.post(
        f"{API}/audit-plans",
        headers=headers,
        json={
            "audit_name": "Procurement FY27",
            "company_id": 1,
            "location_id": 1,
            "period_type": "Quarterly",
            "period_value": "Q2",
            "fiscal_year": "2026-2027",
            "start_date": start,
            "end_date": end,
            "criticality": "Medium",
            "audit_area": "Procurement",
            "caro_status": "CARO",
            "audit_scope_type": "Internal",
        },
    )
    assert resp.status_code == 200, resp.text
    plan_id = resp.json()["id"]
    assert client.post(f"{API}/audit-plans/{plan_id}/submit-for-approval", headers=headers).status_code == 200
    assert client.post(f"{API}/audit-plans/{plan_id}/approve", headers=headers).status_code == 200
    return plan_id


def test_allocation_full_lifecycle(client, setup_database):
    head = auth_headers(client, "superadmin")
    plan_id = _create_approved_plan(client, head)

    available = client.get(f"{API}/audit-allocations/available-plans", headers=head).json()
    assert plan_id in [p["id"] for p in available]

    start = date.today().isoformat()
    end = (date.today() + timedelta(days=30)).isoformat()
    create = client.post(
        f"{API}/audit-allocations",
        headers=head,
        json={
            "audit_plan_id": plan_id,
            "lead_auditor_user_id": 2,
            "mentor_user_id": 1,
            "period_type": "Quarterly",
            "period_value": "Q2",
            "start_date": start,
            "end_date": end,
        },
    )
    assert create.status_code == 200, create.text
    allocation = create.json()
    assert allocation["status"] == "Draft"
    assert allocation["allocation_code"].startswith("ALC-")
    allocation_id = allocation["id"]

    # 1:1 - a second allocation on the same plan is rejected
    dupe = client.post(
        f"{API}/audit-allocations",
        headers=head,
        json={"audit_plan_id": plan_id, "lead_auditor_user_id": 2, "period_value": "Q2", "period_type": "Quarterly", "start_date": start, "end_date": end},
    )
    assert dupe.status_code == 409, dupe.text

    approve = client.post(f"{API}/audit-allocations/{allocation_id}/approve", headers=head)
    assert approve.status_code == 200
    assert approve.json()["status"] == "Allocated"

    initiate = client.post(f"{API}/audit-allocations/{allocation_id}/initiate-audit", headers=head)
    assert initiate.status_code == 200, initiate.text
    audit = initiate.json()
    assert audit["audit_owner_id"] == 2
    assert audit["reviewer_user_id"] == 1
    assert audit["audit_number"].startswith("AUD-")

    # plan no longer allocatable
    available_after = client.get(f"{API}/audit-allocations/available-plans", headers=head).json()
    assert plan_id not in [p["id"] for p in available_after]


def test_auditee_cannot_allocate(client, setup_database):
    head = auth_headers(client, "superadmin")
    plan_id = _create_approved_plan(client, head)
    auditee = auth_headers(client, "auditeeuser1")
    resp = client.post(
        f"{API}/audit-allocations",
        headers=auditee,
        json={"audit_plan_id": plan_id, "lead_auditor_user_id": 2, "period_value": "Q2", "period_type": "Quarterly"},
    )
    assert resp.status_code == 403, resp.text


def test_cannot_allocate_unapproved_plan(client, setup_database):
    head = auth_headers(client, "superadmin")
    start = date.today().isoformat()
    end = (date.today() + timedelta(days=30)).isoformat()
    plan_id = client.post(
        f"{API}/audit-plans",
        headers=head,
        json={
            "audit_name": "Draft Plan",
            "company_id": 1,
            "location_id": 1,
            "period_type": "Quarterly",
            "period_value": "Q3",
            "fiscal_year": "2026-2027",
            "start_date": start,
            "end_date": end,
            "criticality": "Low",
        },
    ).json()["id"]
    resp = client.post(
        f"{API}/audit-allocations",
        headers=head,
        json={"audit_plan_id": plan_id, "lead_auditor_user_id": 2, "period_value": "Q3", "period_type": "Quarterly", "start_date": start, "end_date": end},
    )
    assert resp.status_code == 422, resp.text
