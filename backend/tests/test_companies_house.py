import base64
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.rate_limiter import TokenBucket
from app.dependencies import get_ch_client
from app.main import app
from app.services.companies_house import CompaniesHouseError
from tests.conftest import FAKE_KEY

NUM = "01234567"
STATEMENTS = f"/company/{NUM}/persons-with-significant-control-statements"
EXEMPTIONS = f"/company/{NUM}/exemptions"


def paged(total, page_size=100):
    """respx side effect serving `total` items in CH-style pages."""
    def handler(request: httpx.Request):
        start = int(request.url.params["start_index"])
        size = int(request.url.params["items_per_page"])
        assert size == page_size
        items = [{"n": i} for i in range(start, min(start + size, total))]
        return httpx.Response(200, json={
            "items": items, "total_results": total,
            "start_index": start, "items_per_page": size,
        })
    return handler


# --- new endpoints -------------------------------------------------------------------

def test_psc_statements_endpoint(api, ch_mock):
    route = ch_mock.get(STATEMENTS).respond(200, json={
        "items": [{"statement": "no-individual-or-entity-with-signficant-control"}],
        "total_results": 1, "active_count": 1, "ceased_count": 0,
    })
    r = api.get(f"/companies/{NUM}/pscs/statements")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == [{"statement": "no-individual-or-entity-with-signficant-control"}]
    assert body["total_results"] == 1
    assert body["active_count"] == 1
    assert route.call_count == 1


def test_exemptions_endpoint(api, ch_mock):
    payload = {"kind": "exemptions", "exemptions": {
        "psc_exempt_as_trading_on_regulated_market": {"exemption_type": "x", "items": []},
    }}
    ch_mock.get(EXEMPTIONS).respond(200, json=payload)
    r = api.get(f"/companies/{NUM}/exemptions")
    assert r.status_code == 200
    assert r.json() == payload


def test_new_endpoints_require_auth(ch, ch_mock):
    app.dependency_overrides[get_ch_client] = lambda: ch
    try:
        client = TestClient(app)
        assert client.get(f"/companies/{NUM}/exemptions").status_code == 401
        assert client.get(f"/companies/{NUM}/pscs/statements").status_code == 401
    finally:
        app.dependency_overrides.clear()


# --- pagination ----------------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("get_officers", f"/company/{NUM}/officers"),
    ("get_pscs", f"/company/{NUM}/persons-with-significant-control"),
    ("get_psc_statements", STATEMENTS),
])
async def test_pagination_across_three_pages(ch, ch_mock, method, path):
    route = ch_mock.get(path).mock(side_effect=paged(250))
    result = await getattr(ch, method)(NUM)
    assert route.call_count == 3
    assert [c.request.url.params["start_index"] for c in route.calls] == ["0", "100", "200"]
    assert len(result["items"]) == 250
    assert [i["n"] for i in result["items"]] == list(range(250))
    assert result["total_results"] == 250


def test_statements_endpoint_returns_all_pages(api, ch_mock):
    ch_mock.get(STATEMENTS).mock(side_effect=paged(250))
    r = api.get(f"/companies/{NUM}/pscs/statements")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 250


async def test_pagination_stops_on_empty_page(ch, ch_mock):
    # CH reports 300 but runs dry after 120: must not loop forever.
    def handler(request):
        start = int(request.url.params["start_index"])
        items = [{"n": i} for i in range(start, min(start + 100, 120))]
        return httpx.Response(200, json={"items": items, "total_results": 300})
    route = ch_mock.get(f"/company/{NUM}/officers").mock(side_effect=handler)
    result = await ch.get_officers(NUM)
    assert len(result["items"]) == 120
    assert route.call_count == 3


# --- status passthrough --------------------------------------------------------------

def test_404_passthrough(api, ch_mock):
    route = ch_mock.get(EXEMPTIONS).respond(404, json={"errors": [{"error": "company-profile-not-found"}]})
    r = api.get(f"/companies/{NUM}/exemptions")
    assert r.status_code == 404
    assert route.call_count == 1  # 4xx is not retried


def test_404_passthrough_paginated(api, ch_mock):
    ch_mock.get(STATEMENTS).respond(404)
    assert api.get(f"/companies/{NUM}/pscs/statements").status_code == 404


def test_429_becomes_503_with_retry_after(api, ch_mock):
    route = ch_mock.get(EXEMPTIONS).respond(429, headers={"Retry-After": "42"})
    r = api.get(f"/companies/{NUM}/exemptions")
    assert r.status_code == 503
    assert r.headers["Retry-After"] == "42"
    assert route.call_count == 1  # 429 is not retried


def test_429_retry_after_falls_back_to_ratelimit_reset(api, ch_mock):
    ch_mock.get(EXEMPTIONS).respond(429, headers={
        "X-Ratelimit-Remaining": "0", "X-Ratelimit-Reset": str(int(time.time()) + 30),
    })
    r = api.get(f"/companies/{NUM}/exemptions")
    assert r.status_code == 503
    assert 1 <= int(r.headers["Retry-After"]) <= 31


# --- retries -------------------------------------------------------------------------

async def test_retry_on_502_then_success(ch, ch_mock):
    route = ch_mock.get(EXEMPTIONS).mock(side_effect=[
        httpx.Response(502),
        httpx.Response(200, json={"kind": "exemptions"}),
    ])
    assert await ch.get_exemptions(NUM) == {"kind": "exemptions"}
    assert route.call_count == 2


async def test_retry_on_network_error_then_success(ch, ch_mock):
    route = ch_mock.get(EXEMPTIONS).mock(side_effect=[
        httpx.ConnectError("boom"),
        httpx.Response(200, json={"kind": "exemptions"}),
    ])
    assert await ch.get_exemptions(NUM) == {"kind": "exemptions"}
    assert route.call_count == 2


def test_502_exhausts_two_retries_then_passes_through(api, ch_mock):
    route = ch_mock.get(EXEMPTIONS).respond(502)
    r = api.get(f"/companies/{NUM}/exemptions")
    assert r.status_code == 502
    assert route.call_count == 3  # 1 attempt + 2 retries


async def test_timeout_maps_to_504(ch, ch_mock):
    ch_mock.get(EXEMPTIONS).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(CompaniesHouseError) as exc_info:
        await ch.get_exemptions(NUM)
    assert exc_info.value.status_code == 504


def test_client_timeout_is_10s(ch):
    assert ch._client.timeout.read == 10.0
    assert ch._client.timeout.connect == 10.0


# --- API key handling ----------------------------------------------------------------

def test_api_key_sent_as_basic_auth_and_never_returned_or_logged(api, ch_mock, caplog):
    caplog.set_level("DEBUG")
    encoded = base64.b64encode(f"{FAKE_KEY}:".encode()).decode()
    route = ch_mock.get(EXEMPTIONS).respond(500, text=f"echo {FAKE_KEY}")
    r = api.get(f"/companies/{NUM}/exemptions")
    assert route.calls[0].request.headers["Authorization"] == f"Basic {encoded}"
    for blob in (r.text, str(dict(r.headers)), caplog.text):
        assert FAKE_KEY not in blob
        assert encoded not in blob


async def test_error_object_does_not_carry_key(ch, ch_mock):
    ch_mock.get(EXEMPTIONS).respond(403)
    with pytest.raises(CompaniesHouseError) as exc_info:
        await ch.get_exemptions(NUM)
    assert FAKE_KEY not in repr(exc_info.value)
    assert exc_info.value.status_code == 403


# --- rate limiter --------------------------------------------------------------------

class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_bucket_capacity_is_500_per_5_minutes():
    b = TokenBucket()
    assert b.capacity == 500
    assert b.refill_rate == pytest.approx(500 / 300)


async def test_bucket_drains_and_respects_ratelimit_remaining():
    clock = FakeClock()
    b = TokenBucket(capacity=5, refill_rate=1.0, clock=clock)
    for _ in range(3):
        await b.acquire()
    assert b._tokens == pytest.approx(2)

    b.update_from_headers({"X-Ratelimit-Remaining": "1"})
    assert b._tokens == pytest.approx(1)  # CH's lower count wins

    b.update_from_headers({"X-Ratelimit-Remaining": "0"})
    assert b._tokens == 0
    assert b._blocked_until > clock.t  # pauses until CH's window resets


async def test_ratelimit_headers_feed_the_shared_bucket(ch, ch_mock):
    ch_mock.get(EXEMPTIONS).respond(200, json={}, headers={"X-Ratelimit-Remaining": "7"})
    await ch.get_exemptions(NUM)
    assert ch._limiter._tokens <= 7
