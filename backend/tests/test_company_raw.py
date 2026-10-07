"""GET /companies/{n}/raw and /companies/{n}/officers/raw: CH JSON untouched, always live, never stored."""

from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_ch_client
from app.main import app

NUM = "11391321"
PROFILE = f"/company/{NUM}"
OFFICERS = f"/company/{NUM}/officers"

PROFILE_JSON = {
    "company_number": NUM,
    "company_name": "LIVE LTD",
    "company_status": "active",
    "type": "ltd",
    "date_of_creation": "2018-05-31",
    "sic_codes": ["62012", "62020"],
    "registered_office_address": {"address_line_1": "1 High St", "locality": "London", "postal_code": "N1 1AA"},
    "accounts": {
        "next_due": "2026-03-31",
        "overdue": False,
        "last_accounts": {"made_up_to": "2024-06-30", "type": "micro-entity"},
        "accounting_reference_date": {"day": "30", "month": "06"},
    },
    "confirmation_statement": {"next_due": "2026-06-14", "overdue": False, "last_made_up_to": "2025-05-31"},
    "can_file": True,
    "etag": "abc123",
    "links": {"self": PROFILE},
}


def officer_item(i: int) -> dict:
    return {
        "name": f"PERSON, Mr {i}",
        "officer_role": "director",
        "appointed_on": "2018-05-31",
        "resigned_on": "2020-01-01" if i == 0 else None,
        "country_of_residence": "England",
        "date_of_birth": {"month": 3, "year": 1980},
        "address": {"premises": str(i), "address_line_1": "High St", "locality": "London"},
        "links": {"officer": {"appointments": f"/officers/off{i}/appointments"}},
    }


TOTAL = 150
ALL_ITEMS = [officer_item(i) for i in range(TOTAL)]


def two_pages(request: httpx.Request) -> httpx.Response:
    start = int(request.url.params["start_index"])
    size = int(request.url.params["items_per_page"])
    return httpx.Response(200, json={
        "items": ALL_ITEMS[start:start + size],
        "total_results": TOTAL,
        "active_count": TOTAL - 1,
        "resigned_count": 1,
        "inactive_count": 0,
        "start_index": start,
        "items_per_page": size,
        "links": {"self": OFFICERS},
        "kind": "officer-list",
        "etag": "list-etag",
    })


# --- /raw ---------------------------------------------------------------

def test_profile_raw_returns_untouched_json(api, ch_mock):
    ch_mock.get(PROFILE).respond(200, json=PROFILE_JSON)
    r = api.get(f"/companies/{NUM}/raw")
    assert r.status_code == 200
    assert r.json() == PROFILE_JSON
    assert datetime.fromisoformat(r.headers["X-Fetched-At"]).tzinfo is not None


def test_profile_raw_is_always_live(api, ch_mock):
    route = ch_mock.get(PROFILE).respond(200, json=PROFILE_JSON)
    for _ in range(2):
        assert api.get(f"/companies/{NUM}/raw").status_code == 200
    assert route.call_count == 2


def test_profile_raw_404_passthrough(api, ch_mock):
    ch_mock.get(PROFILE).respond(404)
    assert api.get(f"/companies/{NUM}/raw").status_code == 404


def test_profile_raw_429_becomes_503_with_retry_after(api, ch_mock):
    ch_mock.get(PROFILE).respond(429, headers={"Retry-After": "17"})
    r = api.get(f"/companies/{NUM}/raw")
    assert r.status_code == 503
    assert r.headers["Retry-After"] == "17"


def test_profile_raw_5xx_becomes_502(api, ch_mock):
    ch_mock.get(PROFILE).respond(500)
    assert api.get(f"/companies/{NUM}/raw").status_code == 502


def test_profile_raw_requires_auth(ch, ch_mock):
    app.dependency_overrides[get_ch_client] = lambda: ch
    try:
        assert TestClient(app).get(f"/companies/{NUM}/raw").status_code == 401
    finally:
        app.dependency_overrides.clear()


# --- /officers/raw ------------------------------------------------------

def test_officers_raw_merges_two_pages_untouched(api, ch_mock):
    route = ch_mock.get(OFFICERS).mock(side_effect=two_pages)
    r = api.get(f"/companies/{NUM}/officers/raw")
    assert r.status_code == 200
    assert [c.request.url.params["start_index"] for c in route.calls] == ["0", "100"]
    body = r.json()
    assert body["items"] == ALL_ITEMS
    assert body["items"][0]["country_of_residence"] == "England"
    assert body["total_results"] == TOTAL
    assert body["active_count"] == TOTAL - 1
    assert body["resigned_count"] == 1
    assert body["kind"] == "officer-list"
    assert datetime.fromisoformat(r.headers["X-Fetched-At"]).tzinfo is not None


def test_officers_raw_is_always_live(api, ch_mock):
    route = ch_mock.get(OFFICERS).mock(side_effect=two_pages)
    for _ in range(2):
        assert api.get(f"/companies/{NUM}/officers/raw").status_code == 200
    assert route.call_count == 4


def test_officers_raw_404_passthrough(api, ch_mock):
    ch_mock.get(OFFICERS).respond(404)
    assert api.get(f"/companies/{NUM}/officers/raw").status_code == 404


def test_officers_raw_429_becomes_503(api, ch_mock):
    ch_mock.get(OFFICERS).respond(429, headers={"Retry-After": "9"})
    r = api.get(f"/companies/{NUM}/officers/raw")
    assert r.status_code == 503
    assert r.headers["Retry-After"] == "9"


def test_officers_raw_requires_auth(ch, ch_mock):
    app.dependency_overrides[get_ch_client] = lambda: ch
    try:
        assert TestClient(app).get(f"/companies/{NUM}/officers/raw").status_code == 401
    finally:
        app.dependency_overrides.clear()


# --- CH 401/403 -> 502 --------------------------------------------------

@pytest.mark.parametrize("ch_status", [401, 403])
@pytest.mark.parametrize("suffix", ["/raw", "/officers/raw"])
def test_ch_auth_failure_maps_to_502(api, ch_mock, ch_status, suffix):
    ch_mock.get(PROFILE).respond(ch_status)
    ch_mock.get(OFFICERS).respond(ch_status)
    assert api.get(f"/companies/{NUM}{suffix}").status_code == 502


@pytest.mark.parametrize("ch_status", [401, 403])
def test_ch_auth_failure_maps_to_502_on_stored_profile(db_api, ch_mock, ch_status):
    ch_mock.get(PROFILE).respond(ch_status)
    assert db_api.get(f"/companies/{NUM}").status_code == 502


# --- existing shapes unchanged -----------------------------------------

def test_existing_profile_shape_unchanged(db_api, ch_mock):
    ch_mock.get(PROFILE).respond(200, json=PROFILE_JSON)
    r = db_api.get(f"/companies/{NUM}")
    assert r.status_code == 200
    assert set(r.json()) == {
        "company_number", "company_name", "company_status", "company_type", "date_of_creation",
        "date_of_cessation", "registered_office_address", "sic_codes", "accounts_overdue",
        "confirmation_statement_overdue", "has_charges", "has_insolvency_history", "jurisdiction",
        "risk_flags", "total_officers", "total_pscs", "cached_at",
    }


def test_existing_officers_shape_unchanged(db_api, ch_mock):
    ch_mock.get(PROFILE).respond(200, json=PROFILE_JSON)
    ch_mock.get(OFFICERS).mock(side_effect=two_pages)
    r = db_api.get(f"/companies/{NUM}/officers")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) == TOTAL
    assert set(body[0]) == {
        "id", "name", "role", "appointed_on", "resigned_on", "nationality", "occupation",
        "birth_month", "birth_year", "service_address_line1", "service_address_locality",
        "service_address_postal_code", "service_address_country",
    }
