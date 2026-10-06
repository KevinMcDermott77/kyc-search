import pytest
import respx
from fastapi.testclient import TestClient
from tenacity import wait_none

from app.dependencies import get_ch_client, get_current_user
from app.main import app
from app.services.companies_house import CH_BASE, CompaniesHouseClient

FAKE_KEY = "test-ch-key-do-not-leak"


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
