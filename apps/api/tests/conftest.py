from __future__ import annotations

from collections.abc import Generator
from datetime import date, timedelta
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["API_ENV"] = "test"
os.environ["API_DATABASE_URL"] = "sqlite://"

from app.api.routes.auth import login_attempts
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    Audit,
    AuditPlan,
    City,
    Company,
    Country,
    Designation,
    Location,
    ObservationGrading,
    RiskType,
    RootCause,
    State,
)
from app.schemas.user import UserCreate
from app.services.user import user_service

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[Session, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    login_attempts.clear()
    db = TestingSessionLocal()
    try:
        user_service.ensure_roles_seeded(db)

        country = Country(code="IN", name="India", description="India", created_by="test", updated_by="test")
        state = State(code="KA", name="Karnataka", description="Karnataka", country=country, created_by="test", updated_by="test")
        city = City(code="BLR", name="Bengaluru", description="Bengaluru", state=state, created_by="test", updated_by="test")
        company = Company(name="NHL Limited", country=country, state=state, city=city, pan="AAACN1234Q", gst_no="29AAACN1234Q1Z2", created_by="test", updated_by="test")
        designation_auditor = Designation(code="AUD", title="Auditor", created_by="test", updated_by="test")
        designation_auditee = Designation(code="FIN", title="Finance Manager", created_by="test", updated_by="test")
        location = Location(
            sector="Healthcare",
            country=country,
            state=state,
            city=city,
            company=company,
            location_code="002",
            risk_index="High",
            description="Bengaluru Shared Services",
            created_by="test",
            updated_by="test",
        )
        grading = ObservationGrading(code="HIGH", name="High", severity_rank=2, created_by="test", updated_by="test")
        risk_type = RiskType(code="FIN", name="Financial", description="Financial", created_by="test", updated_by="test")
        root_cause = RootCause(code="DESIGN", name="Control Design Gap", description="Gap", created_by="test", updated_by="test")
        db.add_all([country, state, city, company, designation_auditor, designation_auditee, location, grading, risk_type, root_cause])
        db.flush()

        super_admin = user_service.create_user(
            db,
                UserCreate(
                    username="superadmin",
                    email="superadmin@example.com",
                full_name="Super Admin",
                password="Password@123",
                designation_id=designation_auditor.id,
                company_id=company.id,
                location_id=location.id,
                role_codes=["super_admin"],
            ),
            "test",
        )
        auditor = user_service.create_user(
            db,
                UserCreate(
                    username="auditoruser1",
                    email="auditor@example.com",
                full_name="Auditor User 1",
                password="Password@123",
                designation_id=designation_auditor.id,
                company_id=company.id,
                location_id=location.id,
                role_codes=["auditor"],
            ),
            "test",
        )
        auditee = user_service.create_user(
            db,
                UserCreate(
                    username="auditeeuser1",
                    email="auditee@example.com",
                full_name="Auditee User 1",
                password="Password@123",
                designation_id=designation_auditee.id,
                company_id=company.id,
                location_id=location.id,
                role_codes=["auditee"],
            ),
            "test",
        )
        audit_plan = AuditPlan(
            audit_number="AP-001",
            audit_name="Revenue Review",
            company_id=company.id,
            location_id=location.id,
            quarter="Q1",
            period_type="Quarterly",
            period_value="Q1",
            fiscal_year="2026-2027",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            planned_flag=True,
            criticality="High",
            audit_owner_id=auditor.id,
            created_by="test",
            updated_by="test",
        )
        db.add(audit_plan)
        db.flush()
        audit = Audit(
            audit_plan_id=audit_plan.id,
            audit_number=audit_plan.audit_number,
            audit_name=audit_plan.audit_name,
            company_id=company.id,
            location_id=location.id,
            quarter="Q1",
            period_type="Quarterly",
            period_value="Q1",
            fiscal_year="2026-2027",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status="In Progress",
            planned_flag=True,
            criticality="High",
            audit_owner_id=auditor.id,
            created_by="test",
            updated_by="test",
        )
        db.add(audit)
        db.commit()
        yield db
    finally:
        db.close()


@pytest.fixture
def client(setup_database: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth_headers(client: TestClient, username: str, password: str = "Password@123") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
