from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AuditStatus
from app.models.action_plan import ActionPlan
from app.models.audit import Audit, AuditPlan
from app.models.master import City, Company, Country, Designation, Location, ObservationGrading, RiskType, State
from app.schemas.user import UserCreate
from app.services.user import user_service

from .conftest import auth_headers

SUMMARY = "/api/v1/dashboard/summary"
OPTIONS = "/api/v1/dashboard/filter-options"


def _seeded_audit(db: Session) -> Audit:
    return db.scalars(select(Audit)).first()


def _make_audit(
    db: Session,
    *,
    status: str,
    fiscal_year: str = "2026-2027",
    company_id: int | None = None,
    location_id: int | None = None,
    end_date: date | None = None,
) -> Audit:
    base = _seeded_audit(db)
    resolved_end = end_date or date.today() + timedelta(days=30)
    # ck_audits_date_range requires end_date >= start_date, including for back-dated audits.
    start = min(date.today(), resolved_end)
    audit = Audit(
        audit_number="PLACEHOLDER",  # replaced by the before_insert reference generator
        audit_name=f"{status} audit {fiscal_year}",
        company_id=company_id or base.company_id,
        location_id=location_id or base.location_id,
        quarter="Q1",
        period_type="Quarterly",
        period_value="Q1",
        fiscal_year=fiscal_year,
        start_date=start,
        end_date=resolved_end,
        status=status,
        planned_flag=True,
        criticality="High",
        created_by="test",
        updated_by="test",
    )
    db.add(audit)
    db.flush()
    return audit


def _make_action_plan(db: Session, audit: Audit, *, days_to_timeline: int = 3) -> ActionPlan:
    grading = db.scalars(select(ObservationGrading)).first()
    risk_type = db.scalars(select(RiskType)).first()
    owner = db.scalars(select(Audit.audit_owner_id).where(Audit.id == audit.id)).first()
    if owner is None:
        owner = _seeded_audit(db).audit_owner_id
    plan = ActionPlan(
        audit_id=audit.id,
        audit_number=audit.audit_number,
        location_id=audit.location_id,
        observation_heading=f"Finding for {audit.audit_name}",
        observation_grading_id=grading.id,
        risk_type_id=risk_type.id,
        agreed_timeline=date.today() + timedelta(days=days_to_timeline),
        auditor_status="In Progress",
        auditee_status="In Progress",
        implementation_owner_user_id=owner,
        assigned_auditor_user_id=owner,
        created_by="test",
        updated_by="test",
    )
    db.add(plan)
    db.flush()
    return plan


def _point(payload: dict, label: str) -> int:
    return next(item["value"] for item in payload["audit_status_summary"] if item["label"] == label)


def _get_summary(client, headers, query: str = "") -> dict:
    response = client.get(f"{SUMMARY}{query}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


# --- consistency between the cards and the chart (the reported bug) ---


def test_status_cards_reconcile_to_total(client, setup_database):
    db = setup_database
    for status in [AuditStatus.TO_BE_INITIATED, AuditStatus.COMPLETED, AuditStatus.OVERDUE, AuditStatus.UNPLANNED]:
        _make_audit(db, status=status.value)
    db.commit()

    payload = _get_summary(client, auth_headers(client, "superadmin"))
    assert [item["label"] for item in payload["audit_status_summary"]] == [s.value for s in AuditStatus]
    assert sum(item["value"] for item in payload["audit_status_summary"]) == payload["total_audits"]
    assert payload["total_audits"] == 5  # 1 seeded + 4 created
    assert payload["in_progress"] == _point(payload, AuditStatus.IN_PROGRESS.value)
    assert payload["overdue"] == _point(payload, AuditStatus.OVERDUE.value)
    assert payload["unplanned"] == _point(payload, AuditStatus.UNPLANNED.value)


def test_status_chart_includes_zero_statuses(client, setup_database):
    payload = _get_summary(client, auth_headers(client, "superadmin"))
    labels = [item["label"] for item in payload["audit_status_summary"]]
    assert labels == [status.value for status in AuditStatus]
    assert _point(payload, AuditStatus.COMPLETED.value) == 0
    assert _point(payload, AuditStatus.UNPLANNED.value) == 0
    assert _point(payload, AuditStatus.IN_PROGRESS.value) == 1


def test_overdue_is_status_not_date(client, setup_database):
    db = setup_database
    # Past its end date but still In Progress -> counts as past due, not as Overdue status.
    _make_audit(db, status=AuditStatus.IN_PROGRESS.value, end_date=date.today() - timedelta(days=10))
    # Flagged Overdue by the auditor even though the end date is in the future.
    _make_audit(db, status=AuditStatus.OVERDUE.value, end_date=date.today() + timedelta(days=10))
    db.commit()

    payload = _get_summary(client, auth_headers(client, "superadmin"))
    assert payload["overdue"] == 1
    assert _point(payload, AuditStatus.OVERDUE.value) == 1
    assert payload["past_due_count"] == 1


def test_status_change_moves_card_and_chart_together(client, setup_database):
    """Regression for the reported bug: the chart moved but the cards did not."""
    db = setup_database
    headers = auth_headers(client, "superadmin")
    before = _get_summary(client, headers)
    assert before["in_progress"] == 1
    assert before["unplanned"] == 0

    audit = _seeded_audit(db)
    audit.status = AuditStatus.UNPLANNED.value
    db.commit()

    after = _get_summary(client, headers)
    assert after["unplanned"] == 1
    assert after["in_progress"] == 0
    assert _point(after, AuditStatus.UNPLANNED.value) == 1
    assert _point(after, AuditStatus.IN_PROGRESS.value) == 0
    assert sum(item["value"] for item in after["audit_status_summary"]) == after["total_audits"]


# --- soft deletes ---


def test_soft_deleted_audit_excluded(client, setup_database):
    db = setup_database
    headers = auth_headers(client, "superadmin")
    assert _get_summary(client, headers)["total_audits"] == 1

    audit = _seeded_audit(db)
    audit.is_deleted = True
    db.commit()

    payload = _get_summary(client, headers)
    assert payload["total_audits"] == 0
    assert payload["location_distribution"] == []


def test_soft_deleted_action_plan_excluded(client, setup_database):
    db = setup_database
    audit = _seeded_audit(db)
    _make_action_plan(db, audit)
    deleted = _make_action_plan(db, audit)
    deleted.is_deleted = True
    db.commit()

    payload = _get_summary(client, auth_headers(client, "superadmin"))
    assert payload["total_action_plans"] == 1
    assert sum(item["value"] for item in payload["severity_distribution"]) == 1


def test_action_plan_of_soft_deleted_audit_excluded(client, setup_database):
    db = setup_database
    audit = _make_audit(db, status=AuditStatus.IN_PROGRESS.value)
    _make_action_plan(db, audit)
    db.commit()
    headers = auth_headers(client, "superadmin")
    assert _get_summary(client, headers)["total_action_plans"] == 1

    audit.is_deleted = True
    db.commit()

    payload = _get_summary(client, headers)
    assert payload["total_action_plans"] == 0
    assert payload["severity_distribution"] == []
    assert sum(item["value"] for item in payload["action_plan_aging"]) == 0


# --- filters ---


def test_filter_fiscal_year_narrows_action_plan_metrics(client, setup_database):
    db = setup_database
    this_year = _seeded_audit(db)
    _make_action_plan(db, this_year)
    next_year = _make_audit(db, status=AuditStatus.COMPLETED.value, fiscal_year="2027-2028")
    _make_action_plan(db, next_year)
    db.commit()

    headers = auth_headers(client, "superadmin")
    unfiltered = _get_summary(client, headers)
    assert unfiltered["total_audits"] == 2
    assert unfiltered["total_action_plans"] == 2

    payload = _get_summary(client, headers, "?fiscal_year=2027-2028")
    assert payload["total_audits"] == 1
    assert payload["completed"] == 1
    # Action plans have no fiscal year of their own - this proves the join through Audit works.
    assert payload["total_action_plans"] == 1
    assert sum(item["value"] for item in payload["severity_distribution"]) == 1


def test_filter_company_and_location(client, setup_database):
    db = setup_database
    base = _seeded_audit(db)
    country = db.scalars(select(Country)).first()
    state = db.scalars(select(State)).first()
    city = db.scalars(select(City)).first()
    other_company = Company(
        name="Other Holdings",
        country=country,
        state=state,
        city=city,
        pan="AAACO9876P",
        gst_no="29AAACO9876P1Z9",
        created_by="test",
        updated_by="test",
    )
    db.add(other_company)
    db.flush()
    other_location = Location(
        sector="Manufacturing",
        country=country,
        state=state,
        city=city,
        company=other_company,
        location_code="900",
        risk_index="Medium",
        description="Pune Plant",
        created_by="test",
        updated_by="test",
    )
    db.add(other_location)
    db.flush()
    _make_audit(db, status=AuditStatus.COMPLETED.value, company_id=other_company.id, location_id=other_location.id)
    db.commit()

    headers = auth_headers(client, "superadmin")
    assert _get_summary(client, headers)["total_audits"] == 2

    by_company = _get_summary(client, headers, f"?company_id={other_company.id}")
    assert by_company["total_audits"] == 1
    assert by_company["completed"] == 1

    by_location = _get_summary(client, headers, f"?location_id={other_location.id}")
    assert by_location["total_audits"] == 1
    assert len(by_location["location_distribution"]) == 1
    assert by_location["location_distribution"][0]["label"] == "Pune Plant"

    original = _get_summary(client, headers, f"?company_id={base.company_id}")
    assert original["total_audits"] == 1
    assert original["in_progress"] == 1


def test_filter_status(client, setup_database):
    db = setup_database
    _make_audit(db, status=AuditStatus.COMPLETED.value)
    _make_audit(db, status=AuditStatus.COMPLETED.value)
    db.commit()

    payload = _get_summary(client, auth_headers(client, "superadmin"), "?status=Completed")
    assert payload["total_audits"] == 2
    assert payload["completed"] == 2
    assert _point(payload, AuditStatus.IN_PROGRESS.value) == 0
    assert sum(item["value"] for item in payload["audit_status_summary"]) == payload["total_audits"]


def test_filters_combine_to_zero_rows(client, setup_database):
    payload = _get_summary(client, auth_headers(client, "superadmin"), "?fiscal_year=2099-2100&status=Completed")
    assert payload["total_audits"] == 0
    assert payload["total_action_plans"] == 0
    # Structure must stay valid so the charts never receive a malformed payload.
    assert len(payload["audit_status_summary"]) == len(AuditStatus)
    assert all(item["value"] == 0 for item in payload["audit_status_summary"])
    assert len(payload["action_plan_aging"]) == 2
    assert payload["severity_distribution"] == []
    assert payload["location_distribution"] == []


def test_invalid_status_returns_422(client, setup_database):
    response = client.get(f"{SUMMARY}?status=Nope", headers=auth_headers(client, "superadmin"))
    assert response.status_code == 422, response.text


# --- filter options endpoint ---


def test_filter_options_available_to_management(client, setup_database):
    db = setup_database
    base = _seeded_audit(db)
    designation = db.scalars(select(Designation)).first()
    user_service.create_user(
        db,
        UserCreate(
            username="mgmtuser1",
            email="management@example.com",
            full_name="Management User",
            password="Password@123",
            designation_id=designation.id,
            company_id=base.company_id,
            location_id=base.location_id,
            role_codes=["management"],
        ),
        "test",
    )
    db.commit()

    headers = auth_headers(client, "mgmtuser1")
    response = client.get(OPTIONS, headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["statuses"] == [status.value for status in AuditStatus]
    assert "2026-2027" in payload["fiscal_years"]
    assert payload["companies"] and payload["locations"]
    assert all("company_id" in location for location in payload["locations"])

    # This endpoint exists precisely because Management cannot reach the master data routes.
    forbidden = client.get("/api/v1/master/companies", headers=headers)
    assert forbidden.status_code == 403, forbidden.text


def test_filter_options_forbidden_for_auditee(client, setup_database):
    response = client.get(OPTIONS, headers=auth_headers(client, "auditeeuser1"))
    assert response.status_code == 403, response.text


def test_filter_options_fiscal_years_include_plan_only_years(client, setup_database):
    db = setup_database
    base = _seeded_audit(db)
    db.add(
        AuditPlan(
            audit_number="AP-FUTURE",
            audit_name="Future Plan",
            company_id=base.company_id,
            location_id=base.location_id,
            quarter="Q1",
            period_type="Quarterly",
            period_value="Q1",
            fiscal_year="2030-2031",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            planned_flag=True,
            criticality="High",
            created_by="test",
            updated_by="test",
        )
    )
    db.commit()

    payload = client.get(OPTIONS, headers=auth_headers(client, "superadmin")).json()
    assert "2030-2031" in payload["fiscal_years"]
    # Newest first.
    assert payload["fiscal_years"] == sorted(payload["fiscal_years"], reverse=True)
