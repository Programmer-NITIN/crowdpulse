"""
conftest.py
-----------
Shared test configuration and fixtures for the CrowdPulse test suite.

Design:
- Provides pre-configured test client.
- Resets rate limiter state between test modules.
- Registers custom markers for selective test execution.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.middleware.rate_limiter import (
    navigation_rate_limit,
    chat_rate_limit,
    analytics_rate_limit,
    crowd_rate_limit,
)


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Shared test client for the entire session."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Resets all rate limiter stores between tests to prevent cross-contamination."""
    navigation_rate_limit.store.clear()
    chat_rate_limit.store.clear()
    analytics_rate_limit.store.clear()
    crowd_rate_limit.store.clear()
    yield
    navigation_rate_limit.store.clear()
    chat_rate_limit.store.clear()
    analytics_rate_limit.store.clear()
    crowd_rate_limit.store.clear()
