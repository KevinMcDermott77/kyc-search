"""GET /companies/{n}/pscs/raw: Companies House's PSC JSON untouched, all pages merged, always live."""

from datetime import datetime

import httpx
from fastapi.testclient import TestClient

from app.dependencies import get_ch_client
from app.main import app

NUM = "11391321"
PSCS = f"/company/{NUM}/persons-with-significant-control"


def psc_item(i: int) -> dict:
    if i % 2:
        return {
            "kind": "individual-person-with-significant-control",
            "name": f"Mr Person {i}",
            "name_elements": {"forename": "Person", "surname": str(i), "title": "Mr"},
            "date_of_birth": {"month": 3, "year": 1980},
            "nationality": "British",
            "natures_of_control": ["ownership-of-shares-25-to-50-percent"],
            "notified_on": "2018-05-31",
            "links": {"self": f"/company/{NUM}/persons-with-significant-control/individual/{i}"},
            "etag": f"etag-{i}",
        }
    return {
        "kind": "corporate-entity-person-with-significant-control",
        "name": f"HOLDCO {i} LIMITED",
        "identification": {
            "legal_authority": "Companies Act 2006",
            "legal_form": "Private Limited Company",
            "place_registered": "Companies House",
            "registration_number": f"0{i:07d}",
            "country_registered": "England",
        },
        "natures_of_control": ["ownership-of-shares-75-to-100-percent", "voting-rights-75-to-100-percent"],
        "notified_on": "2018-05-31",
        "ceased_on": "2021-01-01" if i == 0 else None,
        "links": {"self": f"/company/{NUM}/persons-with-significant-control/corporate-entity/{i}"},
        "etag": f"etag-{i}",
    }


TOTAL = 150
ALL_ITEMS = [psc_item(i) for i in range(TOTAL)]


def two_pages(request: httpx.Request) -> httpx.Response:
    start = int(request.url.params["start_index"])
    size = int(request.url.params["items_per_page"])
    return httpx.Response(200, json={
        "items": ALL_ITEMS[start:start + size],
        "total_results": TOTAL,
        "active_count": TOTAL - 1,
        "ceased_count": 1,
        "start_index": start,
        "items_per_page": size,
        "links": {"self": f"/company/{NUM}/persons-with-significant-control"},
        "kind": "persons-with-significant-control#list",
    })


def test_raw_returns_untouched_items_across_two_pages(api, ch_mock):
    route = ch_mock.get(PSCS).mock(side_effect=two_pages)

    r = api.get(f"/companies/{NUM}/pscs/raw")

    assert r.status_code == 200
    assert route.call_count == 2
    assert [c.request.url.params["start_index"] for c in route.calls] == ["0", "100"]
    body = r.json()
    assert body["items"] == ALL_ITEMS  # every item byte-for-byte, incl. identification / ceased_on
    assert body["items"][2]["identification"]["registration_number"] == "00000002"
    assert "linked_company_number" not in body["items"][2]
    assert body["total_results"] == TOTAL
    assert body["active_count"] == TOTAL - 1
    assert body["ceased_count"] == 1
    assert body["links"] == {"self": f"/company/{NUM}/persons-with-significant-control"}
    assert datetime.fromisoformat(r.headers["X-Fetched-At"]).tzinfo is not None


def test_raw_is_always_live(api, ch_mock):
    route = ch_mock.get(PSCS).mock(side_effect=two_pages)
    for _ in range(2):
        assert api.get(f"/companies/{NUM}/pscs/raw").status_code == 200
    assert route.call_count == 4


def test_raw_404_passthrough(api, ch_mock):
    route = ch_mock.get(PSCS).respond(404, json={"errors": [{"error": "company-psc-not-found"}]})
    r = api.get(f"/companies/{NUM}/pscs/raw")
    assert r.status_code == 404
    assert route.call_count == 1


def test_raw_429_becomes_503_with_retry_after(api, ch_mock):
    ch_mock.get(PSCS).respond(429, headers={"Retry-After": "17"})
    r = api.get(f"/companies/{NUM}/pscs/raw")
    assert r.status_code == 503
    assert r.headers["Retry-After"] == "17"


def test_raw_requires_auth(ch, ch_mock):
    app.dependency_overrides[get_ch_client] = lambda: ch
    try:
        assert TestClient(app).get(f"/companies/{NUM}/pscs/raw").status_code == 401
    finally:
        app.dependency_overrides.clear()
