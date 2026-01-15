from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app import app
from app.database.functions import create_all, drop_all

# Import fixtures
from app.tests.fixtures import (  # noqa: F401
    admin_token,
    test_restaurant,
    test_location,
    test_table,
    test_account,
)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def client() -> Generator:
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client(client: TestClient) -> AsyncGenerator:
    async with AsyncClient(
        transport=ASGITransport(app), base_url=client.base_url
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
async def setup_database() -> AsyncGenerator:
    """Setup and teardown database for each test."""
    await drop_all()
    await create_all()
    yield
    await drop_all()