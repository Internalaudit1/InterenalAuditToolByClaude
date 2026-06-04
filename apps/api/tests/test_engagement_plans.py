from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import City, Company, Country, Location, State
from app.schemas.user import UserCreate
from app.models.engagement import EngagementPlan
from app.services.user import user_service

from .conftest import auth_headers


def create_head_auditor(db: Session) -> None:
    if user_service.get_by_username(db, "headauditor1"):
        return
    company_id = db.scalar(select(EngagementPlan.company_id).limit(1))
    location_id = db.scalar(select(EngagementPlan.location_id).limit(1))
    if company_id is None or location_id is None:
        company_id = 1
        location_id = 1
    user_service.create_user(
        db,
        UserCreate(
            username="headauditor1",
            email="head.auditor@example.com",
            full_name="Head Auditor 1",
            password="Password@123",
            company_id=company_id,
            location_id=location_id,
            role_codes=["head_auditor"],
        ),
        "test",
    )
    db.commit()


def create_auditor(db: Session, *, username: str, full_name: str, email: str) -> None:
    if user_service.get_by_username(db, username):
        return
    company_id = db.scalar(select(EngagementPlan.company_id).limit(1))
    location_id = db.scalar(select(EngagementPlan.location_id).limit(1))
    if company_id is None or location_id is None:
        company_id = 1
        location_id = 1
    user_service.create_user(
        db,
        UserCreate(
            username=username,
            email=email,
            full_name=full_name,
            password="Password@123",
            company_id=company_id,
            location_id=location_id,
            role_codes=["auditor"],
        ),
        "test",
    )
    db.commit()


def test_engagement_plan_create_submit_approve_and_kickoff(client, setup_database: Session):
    create_head_auditor(setup_database)
    auditor_headers = auth_headers(client, "auditoruser1")
    head_headers = auth_headers(client, "headauditor1")

    create_response = client.post(
        "/api/v1/engagement-plans",
        headers=auditor_headers,
        json={
            "audit_id": 1,
            "title": "Revenue Q1 FY26 Engagement",
            "objective": "Validate revenue recognition controls.",
            "scope": "Revenue cycle walkthroughs and sample testing.",
            "scope_exclusions": "No tax provisioning review.",
            "planned_start_date": "2026-04-24",
            "planned_end_date": "2026-05-15",
            "lead_auditor_id": 2,
            "planned_hours": 40,
        },
    )
    assert create_response.status_code == 200, create_response.text
    engagement_id = create_response.json()["id"]
    assert create_response.json()["status"] == "Draft"
    assert create_response.json()["engagement_code"].startswith("ENG-")

    submit_response = client.post(
        f"/api/v1/engagement-plans/{engagement_id}/submit",
        headers=auditor_headers,
        json={},
    )
    assert submit_response.status_code == 200, submit_response.text
    assert submit_response.json()["status"] == "Submitted"

    approve_response = client.post(
        f"/api/v1/engagement-plans/{engagement_id}/approve",
        headers=head_headers,
        json={"remarks": "Proceed to kickoff."},
    )
    assert approve_response.status_code == 200, approve_response.text
    assert approve_response.json()["status"] == "Approved"

    checklist_response = client.get(
        f"/api/v1/engagement-plans/{engagement_id}/kickoff-checklist",
        headers=auditor_headers,
    )
    assert checklist_response.status_code == 200, checklist_response.text
    checklist_items = checklist_response.json()
    assert checklist_items

    save_checklist_response = client.patch(
        f"/api/v1/engagement-plans/{engagement_id}/kickoff-checklist",
        headers=auditor_headers,
        json={
            "items": [
                {
                    "id": item["id"],
                    "check_item": item["check_item"],
                    "is_mandatory": item["is_mandatory"],
                    "is_completed": True if item["is_mandatory"] else item["is_completed"],
                    "remarks": "Completed during kickoff.",
                }
                for item in checklist_items
            ]
        },
    )
    assert save_checklist_response.status_code == 200, save_checklist_response.text

    detail_response = client.get(
        f"/api/v1/engagement-plans/{engagement_id}",
        headers=auditor_headers,
    )
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["status"] == "Kicked Off"


def test_engagement_plan_prefill_uses_assigned_audit_defaults(client, setup_database: Session):
    auditor_headers = auth_headers(client, "auditoruser1")

    response = client.get("/api/v1/engagement-plans/prefill/1", headers=auditor_headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["audit_id"] == 1
    assert payload["audit_number"].startswith("AUD-")
    assert payload["lead_auditor_id"] == 2
    assert payload["planned_start_date"] == payload["audit_period_from"]
    assert payload["planned_end_date"] == payload["audit_period_to"]
    assert payload["can_create"] is True


def test_engagement_plan_prefill_blocks_unassigned_auditor(client, setup_database: Session):
    create_auditor(
        setup_database,
        username="auditoruser2",
        full_name="Auditor User 2",
        email="auditor2@example.com",
    )
    other_auditor_headers = auth_headers(client, "auditoruser2")

    response = client.get("/api/v1/engagement-plans/prefill/1", headers=other_auditor_headers)

    assert response.status_code == 403, response.text


def test_assigned_lead_auditor_can_prefill_even_when_user_master_scope_differs(client, setup_database: Session):
    auditor = user_service.get_by_username(setup_database, "auditoruser1")
    assert auditor is not None

    country = Country(code="GB", name="United Kingdom", description="United Kingdom", created_by="test", updated_by="test")
    state = State(code="LN", name="London", description="London", country=country, created_by="test", updated_by="test")
    city = City(code="LON", name="London", description="London", state=state, created_by="test", updated_by="test")
    company = Company(
        name="UK Audit Entity",
        country=country,
        state=state,
        city=city,
        pan="AAACU1234Q",
        gst_no="29AAACU1234Q1Z2",
        created_by="test",
        updated_by="test",
    )
    location = Location(
        sector="Shared Services",
        country=country,
        state=state,
        city=city,
        company=company,
        location_code="UK01",
        risk_index="Medium",
        description="London Operations",
        created_by="test",
        updated_by="test",
    )
    setup_database.add_all([country, state, city, company, location])
    setup_database.flush()

    auditor.company_id = company.id
    auditor.location_id = location.id
    setup_database.flush()
    setup_database.commit()

    auditor_headers = auth_headers(client, "auditoruser1")

    audits_response = client.get("/api/v1/audits?page_size=100&scope=mine", headers=auditor_headers)
    assert audits_response.status_code == 200, audits_response.text
    audit_ids = {item["id"] for item in audits_response.json()["items"]}
    assert 1 in audit_ids

    prefill_response = client.get("/api/v1/engagement-plans/prefill/1", headers=auditor_headers)
    assert prefill_response.status_code == 200, prefill_response.text
    assert prefill_response.json()["audit_id"] == 1


def test_engagement_plan_create_defaults_lead_auditor_from_assigned_audit(client, setup_database: Session):
    auditor_headers = auth_headers(client, "auditoruser1")

    create_response = client.post(
        "/api/v1/engagement-plans",
        headers=auditor_headers,
        json={
            "audit_id": 1,
            "title": "Auto Lead Mapping Engagement",
            "objective": "Use assigned lead from the initiated audit.",
            "scope": "Validate assigned-audit handoff.",
            "planned_start_date": "2026-04-24",
            "planned_end_date": "2026-05-10",
        },
    )

    assert create_response.status_code == 200, create_response.text
    assert create_response.json()["lead_auditor_id"] == 2


def test_head_auditor_only_can_approve_engagement_plan(client, setup_database: Session):
    create_head_auditor(setup_database)
    auditor_headers = auth_headers(client, "auditoruser1")

    create_response = client.post(
        "/api/v1/engagement-plans",
        headers=auditor_headers,
        json={
            "audit_id": 1,
            "title": "Treasury Readiness Engagement",
            "objective": "Prepare for treasury fieldwork.",
            "scope": "Treasury process walkthrough.",
            "planned_start_date": "2026-04-24",
            "planned_end_date": "2026-05-10",
            "lead_auditor_id": 2,
        },
    )
    assert create_response.status_code == 200, create_response.text
    engagement_id = create_response.json()["id"]

    submit_response = client.post(
        f"/api/v1/engagement-plans/{engagement_id}/submit",
        headers=auditor_headers,
        json={},
    )
    assert submit_response.status_code == 200, submit_response.text

    approve_response = client.post(
        f"/api/v1/engagement-plans/{engagement_id}/approve",
        headers=auditor_headers,
        json={"remarks": "Trying to self-approve."},
    )
    assert approve_response.status_code == 403, approve_response.text
