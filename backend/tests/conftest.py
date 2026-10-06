import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tenacity import wait_none

from app.db.base import Base
from app.db.session import get_db
from app.dependencies import get_ch_client, get_current_user
from app.main import app
from app.routers import companies
from app.services.companies_house import CH_BASE, CompaniesHouseClient

FAKE_KEY = "test-ch-key-do-not-leak"
NOW = datetime.now(timezone.utc)


@pytest.fixture
def ch_mock():
    with respx.mock(base_url=CH_BASE, assert_all_called=False) as mock:
        yield mock


@pytest.fixture
def ch():
    return CompaniesHouseClient(api_key=FAKE_KEY, retry_wait=wait_none())


@pytest.fixture
def api(ch):
    app.dependency_overrides[get_ch_client] = lambda: ch
    app.dependency_overrides[get_current_user] = lambda: object()
    try:
        yield TestClient(app)  # no context manager: skips the DB lifespan
    finally:
        app.dependency_overrides.clear()


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
