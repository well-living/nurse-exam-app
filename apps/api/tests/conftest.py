import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app, settings
from db import db


@pytest.fixture(autouse=True)
def disable_db():
    """Disable database connection for all tests by default."""
    original_url = settings.database_url
    settings.database_url = ""
    db.pool = None
    yield
    settings.database_url = original_url


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


@pytest.fixture
def mock_db():
    """Mock database connection for testing."""
    mock_pool = MagicMock()
    mock_connection = AsyncMock()

    # Create a context manager that returns the mock connection
    class MockAcquire:
        async def __aenter__(self):
            return mock_connection
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_pool.acquire.return_value = MockAcquire()

    original_pool = db.pool
    db.pool = mock_pool

    yield mock_connection

    db.pool = original_pool


@pytest.fixture
def sample_user_id():
    """Generate a sample user UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_question_id():
    """Generate a sample question UUID."""
    return uuid.uuid4()
