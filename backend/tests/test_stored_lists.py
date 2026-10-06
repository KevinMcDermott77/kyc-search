"""Storage freshness for /officers and /pscs; liveness for /pscs/statements and /exemptions."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.base import Base
from app.db.session import get_db
from app.dependencies import get_ch_client, get_current_user
from app.main import app
from app.models import Company, Officer, Psc
from app.routers import companies

NUM = "01234567"
NOW = datetime.now(timezone.utc)

KINDS = {
    "officers": dict(
        model=Officer,
        ch_path=f"/company/{NUM}/officers",
        stored=lambda cid: Officer(company_id=cid, company_number=NUM, name="STORED OFFICER", role="director"),
        ch_item={"name": "LIVE OFFICER", "officer_role": "director"},
        live_name="LIVE OFFICER",
    ),
    "pscs": dict(
        model=Psc,
        ch_path=f"/company/{NUM}/persons-with-significant-control",
        stored=lambda cid: Psc(company_id=cid, company_number=NUM, name="STORED PSC",
                               kind="individual-person-with-significant-control"),
        ch_item={"name": "LIVE PSC", "kind": "individual-person-with-significant-control"},
        live_name="LIVE PSC",
    ),
}


@pytest.fixture
def sessionmaker(tmp_path):
    # NullPool: the seeding loop and the TestClient loop must not share connections.
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}", poolclass=NullPool)

    async def create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create())
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
def db_api(sessionmaker, ch, monkeypatch):
    # Default: this process "started" long ago, so only the 24h rule applies.
    monkeypatch.setattr(companies, "PAGINATED_SINCE", NOW - timedelta(days=30))

    async def override_db():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_ch_client] = lambda: ch
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def seed(sessionmaker, kind: str, cached_at: datetime) -> None:
    async def run():
        async with sessionmaker() as db:
            # Fresh company profile so _get_or_fetch_company does not call CH.
            company = Company(company_number=NUM, company_name="TEST LTD", last_full_fetch=NOW)
            db.add(company)
            await db.flush()
            row = KINDS[kind]["stored"](company.id)
            row.cached_at = cached_at
            db.add(row)
            await db.commit()

    asyncio.run(run())


def stored_names(sessionmaker, kind: str) -> list[str]:
    async def run():
        async with sessionmaker() as db:
            return list((await db.execute(select(KINDS[kind]["model"].name))).scalars())

    return asyncio.run(run())


def mock_live(ch_mock, kind: str):
    return ch_mock.get(KINDS[kind]["ch_path"]).mock(return_value=httpx.Response(
        200, json={"items": [KINDS[kind]["ch_item"]], "total_results": 1},
    ))


@pytest.mark.parametrize("kind", KINDS)
def test_row_under_24h_is_served_from_storage(db_api, sessionmaker, ch_mock, kind):
    cached_at = NOW - timedelta(hours=23)
    seed(sessionmaker, kind, cached_at)
    route = mock_live(ch_mock, kind)

    r = db_api.get(f"/companies/{NUM}/{kind}")

    assert r.status_code == 200
    assert route.call_count == 0
    assert [i["name"] for i in r.json()] == [KINDS[kind]["stored"](0).name]
    assert datetime.fromisoformat(r.headers["X-Fetched-At"]) == cached_at


@pytest.mark.parametrize("kind", KINDS)
def test_stale_rows_trigger_refetch_and_are_replaced(db_api, sessionmaker, ch_mock, kind):
    seed(sessionmaker, kind, NOW - timedelta(hours=25))
    route = mock_live(ch_mock, kind)

    r = db_api.get(f"/companies/{NUM}/{kind}")

    assert r.status_code == 200
    assert route.call_count == 1
    assert [i["name"] for i in r.json()] == [KINDS[kind]["live_name"]]
    assert stored_names(sessionmaker, kind) == [KINDS[kind]["live_name"]]
    assert datetime.fromisoformat(r.headers["X-Fetched-At"]) >= NOW


@pytest.mark.parametrize("kind", KINDS)
def test_rows_saved_before_pagination_trigger_refetch(db_api, sessionmaker, ch_mock, monkeypatch, kind):
    seed(sessionmaker, kind, NOW - timedelta(hours=1))
    monkeypatch.setattr(companies, "PAGINATED_SINCE", NOW)  # row predates this process
    route = mock_live(ch_mock, kind)

    r = db_api.get(f"/companies/{NUM}/{kind}")

    assert route.call_count == 1
    assert [i["name"] for i in r.json()] == [KINDS[kind]["live_name"]]


@pytest.mark.parametrize("kind", KINDS)
def test_fresh_true_bypasses_storage(db_api, sessionmaker, ch_mock, kind):
    seed(sessionmaker, kind, NOW - timedelta(minutes=5))
    route = mock_live(ch_mock, kind)

    r = db_api.get(f"/companies/{NUM}/{kind}", params={"fresh": "true"})

    assert r.status_code == 200
    assert route.call_count == 1
    assert [i["name"] for i in r.json()] == [KINDS[kind]["live_name"]]
    assert stored_names(sessionmaker, kind) == [KINDS[kind]["live_name"]]


@pytest.mark.parametrize("kind", KINDS)
def test_response_shape_is_still_a_list(db_api, sessionmaker, ch_mock, kind):
    seed(sessionmaker, kind, NOW - timedelta(hours=1))
    r = db_api.get(f"/companies/{NUM}/{kind}")
    assert isinstance(r.json(), list)


@pytest.mark.parametrize("path,ch_path", [
    ("pscs/statements", f"/company/{NUM}/persons-with-significant-control-statements"),
    ("exemptions", f"/company/{NUM}/exemptions"),
])
def test_statements_and_exemptions_are_always_live(db_api, sessionmaker, ch_mock, path, ch_path):
    route = ch_mock.get(ch_path).respond(200, json={"items": [], "total_results": 0})
    for _ in range(2):
        assert db_api.get(f"/companies/{NUM}/{path}").status_code == 200
    assert route.call_count == 2
