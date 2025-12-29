"""
Pytest configuration and fixtures for backend tests.
"""
import pytest
from unittest.mock import MagicMock, patch

# Mock environment for tests
TEST_ENV = {
    "ENVIRONMENT": "test",
    "REDIS_URL": "redis://localhost:6379/1",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
    "OPENAI_API_KEY": "sk-test-key",
}


@pytest.fixture
def mock_settings():
    """Provide mock settings for tests."""
    with patch.dict("os.environ", TEST_ENV):
        yield


@pytest.fixture
def mock_supabase():
    """Provide mock Supabase client."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.execute.return_value.data = []
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-id"}]
    with patch("backend.state.impl.supabase_store.get_supabase_client", return_value=mock_client):
        yield mock_client


@pytest.fixture
def sample_job_config():
    """Provide sample job configuration."""
    return {
        "topic": "Test research topic",
        "mode": "investigation",
        "user_id": "test-user-123",
    }
