import os
from collections.abc import AsyncIterator, Iterator

# Must be set before anything imports ledgermap.db.session, which builds its
# engine from settings at import time. Tests delete every row after each run,
# so they get their own database (`make test` creates and migrates it) rather
# than the development one.
TEST_DATABASE_URL = (
    "postgresql+asyncpg://ledgermap:ledgermap@localhost:5432/ledgermap_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from ledgermap.config import Settings, get_settings  # noqa: E402
from ledgermap.db.session import engine  # noqa: E402
from ledgermap.main import app  # noqa: E402

# Tables in child-to-parent FK order so TRUNCATE ... CASCADE isn't required.
_TABLES_IN_DELETE_ORDER = (
    "chat_messages",
    "corrections",
    "run_line_items",
    "runs",
    "account_mappings",
    "taxonomy_entries",
    "taxonomies",
    "clients",
)


@pytest.fixture(autouse=True)
def _ignore_local_env_file(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Build settings from code defaults plus explicit env vars only, never a
    developer's `.env` — otherwise e.g. LLM_CLASSIFICATION_ENABLED=true there
    makes every upload test call a real model."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
        # Last line of defence against wiping real data if the URL above is
        # ever changed or overridden.
        assert engine.url.database.endswith("_test"), engine.url.database
        async with engine.begin() as connection:
            for table in _TABLES_IN_DELETE_ORDER:
                await connection.execute(text(f"DELETE FROM {table}"))
        await engine.dispose()
