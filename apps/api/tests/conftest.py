import pytest
from httpx import ASGITransport, AsyncClient

from main import app, settings


@pytest.fixture
def enable_debug():
    """Enable debug mode for testing."""
    original = settings.debug
    settings.debug = True
    yield
    settings.debug = original


@pytest.fixture
def set_allowlist():
    """Set allowlist for testing."""
    original_debug = settings.debug
    original_allowlist = settings.allowlist_emails
    settings.debug = False
    settings.allowlist_emails = "allowed@example.com,admin@example.com"
    yield
    settings.debug = original_debug
    settings.allowlist_emails = original_allowlist


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
