from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import City, Company, Country, State
from tests.conftest import auth_headers


def _add_uk_geography(db: Session) -> tuple[Country, State, City]:
    country = Country(code="UK", name="United Kingdom", description="United Kingdom", created_by="test", updated_by="test")
    state = State(code="LDN", name="London", description="London", country=country, created_by="test", updated_by="test")
    city = City(code="LON", name="London", description="London", state=state, created_by="test", updated_by="test")
    db.add_all([country, state, city])
    db.commit()
    db.refresh(country)
    db.refresh(state)
    db.refresh(city)
    return country, state, city


def test_location_rejects_state_that_does_not_belong_to_country(client, setup_database: Session):
    _, london_state, london_city = _add_uk_geography(setup_database)
    india = setup_database.scalar(select(Country).where(Country.code == "IN"))
    company = setup_database.scalar(select(Company).where(Company.name == "NHL Limited"))

    response = client.post(
        "/api/v1/master/locations",
        headers=auth_headers(client, "superadmin"),
        json={
            "sector": "Healthcare",
            "country_id": india.id,
            "state_id": london_state.id,
            "city_id": london_city.id,
            "company_id": company.id,
            "location_code": "GEO-BLOCK-1",
            "risk_index": "Low",
            "description": "Invalid geography chain",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Selected state does not belong to the selected country."


def test_location_rejects_city_that_does_not_belong_to_state(client, setup_database: Session):
    _, _, london_city = _add_uk_geography(setup_database)
    india = setup_database.scalar(select(Country).where(Country.code == "IN"))
    karnataka = setup_database.scalar(select(State).where(State.code == "KA"))
    company = setup_database.scalar(select(Company).where(Company.name == "NHL Limited"))

    response = client.post(
        "/api/v1/master/locations",
        headers=auth_headers(client, "superadmin"),
        json={
            "sector": "Healthcare",
            "country_id": india.id,
            "state_id": karnataka.id,
            "city_id": london_city.id,
            "company_id": company.id,
            "location_code": "GEO-BLOCK-2",
            "risk_index": "Low",
            "description": "Invalid city chain",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Selected city does not belong to the selected state."


def test_company_rejects_state_that_does_not_belong_to_country(client, setup_database: Session):
    _, london_state, london_city = _add_uk_geography(setup_database)
    india = setup_database.scalar(select(Country).where(Country.code == "IN"))

    response = client.post(
        "/api/v1/master/companies",
        headers=auth_headers(client, "superadmin"),
        json={
            "name": "Invalid Geography Company",
            "country_id": india.id,
            "state_id": london_state.id,
            "city_id": london_city.id,
            "pan": "AAACI1234Q",
            "gst_no": "29AAACI1234Q1Z2",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Selected state does not belong to the selected country."
