"""
conftest.py
-----------
Shared test configuration, fixtures, and helpers for the CrowdPulse test suite.

Design:
- Provides pre-configured test client for API integration tests.
- Resets rate limiter state between test modules to prevent cross-contamination.
- Centralizes common test data (density maps, predictions, zone scores)
  so test files stay DRY and consistent.
- Registers custom markers for selective test execution.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import ZONE_REGISTRY
from app.main import app
from app.middleware.rate_limiter import (
    navigation_rate_limit,
    chat_rate_limit,
    analytics_rate_limit,
    crowd_rate_limit,
)


# ── Client Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client() -> TestClient:
    """Shared test client for the entire session."""
    return TestClient(app)


# ── Rate Limiter Reset ───────────────────────────────────────────────────────

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


# ── Shared Test Data ─────────────────────────────────────────────────────────

@pytest.fixture()
def sample_density_map() -> dict[str, int]:
    """Returns a realistic density map covering all zones in the registry.

    Provides a stable baseline for tests that need crowd density data
    without depending on the time-sensitive simulator.
    """
    return {zone_id: 50 for zone_id in ZONE_REGISTRY}


@pytest.fixture()
def sample_predictions(sample_density_map) -> dict[str, dict]:
    """Returns stable predictions for all zones.

    Each zone gets a STABLE trend and a predicted density equal to
    the current density — suitable for deterministic routing tests.
    """
    return {
        zone_id: {
            "zone_id": zone_id,
            "current_density": density,
            "predicted_density": density,
            "trend": "STABLE",
            "prediction_window_minutes": 30,
            "inflow_rate": 0.0,
            "outflow_rate": 0.0,
            "flow_delta": 0,
        }
        for zone_id, density in sample_density_map.items()
    }


@pytest.fixture()
def sample_zone_scores(sample_density_map, sample_predictions) -> dict[str, dict]:
    """Returns pre-computed zone scores for all zones.

    Uses the scorer module to produce realistic scores from the
    sample density map and predictions.
    """
    from app.decision_engine.scorer import score_all_zones
    return score_all_zones(sample_density_map, sample_predictions, "live")


@pytest.fixture()
def nav_headers() -> dict[str, str]:
    """Returns headers with a unique forwarded IP for rate-limiter isolation."""
    return {"X-Forwarded-For": "10.203.0.1"}
