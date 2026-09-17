from httpx import ASGITransport, AsyncClient
import pytest_asyncio

from ledgermap.main import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client