"""Pytest fixtures for DevPilot backend tests."""

import pytest
from fastapi.testclient import TestClient
from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure all tables exist for testing when database is available."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        # Fallback for unit test environments where database is mocked or disconnected
        pass
    yield


@pytest.fixture(scope="session")
def client(setup_test_db):
    """Create a FastAPI test client instance."""
    with TestClient(app) as test_client:
        yield test_client
