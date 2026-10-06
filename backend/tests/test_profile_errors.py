"""GET /companies/{n}: upstream and database failures map to 502/503/504, never an unmapped 500."""

import httpx
import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app.models import Company
from app.services import ingestion
from tests.conftest import FAKE_KEY, NOW

NUM = "11391321"
PROFILE = f"/company/{NUM}"
PROFILE_JSON = {"company_number": NUM, "company_name": "LIVE LTD", "company_status": "active"}


@pytest.mark.parametrize("ch_status,expected", [(500, 502), (502, 502), (503, 503), (504, 504)])
def test_ch_5xx_maps_to_gateway_status(db_api, ch_mock, ch_status, expected):
    route = ch_mock.get(PROFILE).respond(ch_status)
    r = db_api.get(f"/companies/{NUM}")
    assert r.status_code == expected
    assert route.call_count == 3  # retried first


def test_ch_timeout_maps_to_504(db_api, ch_mock):
    ch_mock.get(PROFILE).mock(side_effect=httpx.ReadTimeout("slow"))
    assert db_api.get(f"/companies/{NUM}").status_code == 504


def test_ch_network_error_maps_to_502_and_logs_type_only(db_api, ch_mock, caplog):
    caplog.set_level("WARNING")
    ch_mock.get(PROFILE).mock(side_effect=httpx.ConnectError(f"boom {FAKE_KEY}"))
    assert db_api.get(f"/companies/{NUM}").status_code == 502
    assert "ConnectError" in caplog.text
    assert FAKE_KEY not in caplog.text


def test_ch_non_json_body_maps_to_502(db_api, ch_mock):
    ch_mock.get(PROFILE).respond(200, text="<html>Service maintenance</html>")
    assert db_api.get(f"/companies/{NUM}").status_code == 502


def test_ch_undecodable_body_maps_to_502(db_api, ch_mock):
    ch_mock.get(PROFILE).mock(side_effect=httpx.DecodingError("bad gzip"))
    assert db_api.get(f"/companies/{NUM}").status_code == 502


def test_ch_404_still_passes_through(db_api, ch_mock):
    ch_mock.get(PROFILE).respond(404)
    assert db_api.get(f"/companies/{NUM}").status_code == 404


def test_db_connection_failure_maps_to_503(db_api, ch_mock, monkeypatch, caplog):
    caplog.set_level("WARNING")
    ch_mock.get(PROFILE).respond(200, json=PROFILE_JSON)

    async def lost_connection(*args, **kwargs):
        raise OperationalError("UPDATE companies ...", {"secret": FAKE_KEY}, Exception("connection reset"))

    monkeypatch.setattr(ingestion, "ingest_company", lost_connection)
    r = db_api.get(f"/companies/{NUM}")
    assert r.status_code == 503
    assert r.headers["Retry-After"]
    assert "OperationalError" in caplog.text
    assert FAKE_KEY not in caplog.text


def test_concurrent_first_fetch_reuses_row_instead_of_500(db_api, sessionmaker, ch_mock, monkeypatch):
    """Two requests for a new company both insert; the loser must serve the winner's row."""
    ch_mock.get(PROFILE).respond(200, json=PROFILE_JSON)

    async def lose_the_race(db, raw, **kwargs):
        async with sessionmaker() as other:
            other.add(Company(company_number=NUM, company_name="WINNER LTD", last_full_fetch=NOW))
            await other.commit()
        raise IntegrityError("INSERT INTO companies ...", {}, Exception("duplicate key"))

    monkeypatch.setattr(ingestion, "ingest_company", lose_the_race)
    r = db_api.get(f"/companies/{NUM}")
    assert r.status_code == 200
    assert r.json()["company_name"] == "WINNER LTD"


def test_profile_happy_path(db_api, ch_mock):
    ch_mock.get(PROFILE).respond(200, json=PROFILE_JSON)
    r = db_api.get(f"/companies/{NUM}")
    assert r.status_code == 200
    assert r.json()["company_name"] == "LIVE LTD"
