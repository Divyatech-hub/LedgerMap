from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text

from ledgermap.db.session import engine
from ledgermap.main import app

# Tables in child-to-parent FK order so TRUNCATE ... CASCADE isn't required.
_TABLES_IN_DELETE_ORDER = (
    "corrections",
    "run_line_items",
    "runs",
    "account_mappings",
    "taxonomy_entries",
    "taxonomies",
    "clients",
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def db_client() -> AsyncIterator[TestClient]:
    """A TestClient backed by the real database (see docker-compose.yml,
    `make db-up`), truncated clean after the test runs.

    Each request opens its own session against the shared engine rather than
    reusing one across the test's event loop and the TestClient's internal
    portal thread, which run on different event loops and can't share an
    asyncpg connection.
    """
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        # The pool's connections were opened on the TestClient portal's event
        # loop; discard them before reconnecting on this fixture's loop, since
        # asyncpg connections can't be reused across event loops.
        await engine.dispose()
        async with engine.begin() as connection:
            for table in _TABLES_IN_DELETE_ORDER:
                await connection.execute(text(f"DELETE FROM {table}"))
        await engine.dispose()
