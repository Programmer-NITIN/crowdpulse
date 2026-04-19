"""
tests/test_google_services.py
-------------------------------
Tests for all 7 Google Service integrations to verify:
- Mock fallback behaviour is correct.
- Data returned matches expected schemas.
- Graceful degradation when services are unavailable.
"""

from app.google_services import (
    firestore_client,
    bigquery_client,
    maps_client,
    cloud_logging,
    firebase_auth,
)
from app.config import ZONE_REGISTRY


# ── Firestore ────────────────────────────────────────────────────────────────

class TestFirestoreMock:
    """Tests for in-memory Firestore mock store."""

    def test_store_and_retrieve_document(self):
        firestore_client.store_document("test_col", "doc1", {"key": "value"})
        doc = firestore_client.get_document("test_col", "doc1")
        assert doc is not None
        assert doc["key"] == "value"

    def test_retrieve_nonexistent_document(self):
        doc = firestore_client.get_document("test_col", "nonexistent_12345")
        assert doc is None

    def test_list_documents(self):
        firestore_client.store_document("list_test", "a1", {"n": 1})
        firestore_client.store_document("list_test", "a2", {"n": 2})
        docs = firestore_client.list_documents("list_test")
        assert len(docs) >= 2

    def test_stored_document_has_timestamp(self):
        firestore_client.store_document("ts_test", "ts1", {"x": 1})
        doc = firestore_client.get_document("ts_test", "ts1")
        assert "_stored_at" in doc

    def test_mock_store_is_bounded(self):
        """Verify the mock store evicts oldest entries beyond capacity."""
        from app.google_services.firestore_client import _mock_store
        original_max = _mock_store._max
        _mock_store._max = 5
        for i in range(10):
            firestore_client.store_document("evict_test", f"doc_{i}", {"i": i})
        assert _mock_store.size <= 5
        _mock_store._max = original_max

    def test_is_using_mock(self):
        assert firestore_client.is_using_mock() is True


# ── BigQuery ─────────────────────────────────────────────────────────────────

class TestBigQueryMock:
    """Tests for BigQuery mock analytics data."""

    def test_hotspots_returns_list(self):
        result = bigquery_client.get_historical_hotspots(top_n=5)
        assert isinstance(result, list)
        assert len(result) <= len(ZONE_REGISTRY)

    def test_hotspots_returns_strings(self):
        result = bigquery_client.get_historical_hotspots()
        assert all(isinstance(h, str) for h in result)

    def test_peak_density_schema(self):
        result = bigquery_client.get_peak_density_history("GA")
        assert "zone_id" in result
        assert "avg_peak_density" in result
        assert "max_peak_density" in result
        assert "sample_count" in result

    def test_peak_density_values_in_range(self):
        result = bigquery_client.get_peak_density_history("ST")
        assert 0 <= result["avg_peak_density"] <= 100
        assert 0 <= result["max_peak_density"] <= 100

    def test_hotspots_top_n_clamped(self):
        """Verify top_n is clamped to [1, 20]."""
        result = bigquery_client.get_historical_hotspots(top_n=100)
        assert len(result) <= 20

    def test_is_using_mock(self):
        assert bigquery_client.is_using_mock() is True


# ── Maps ─────────────────────────────────────────────────────────────────────

class TestMapsMock:
    """Tests for Google Maps Platform mock client."""

    def test_walking_distance_returns_int(self):
        distance = maps_client.get_walking_distance("GA", "MC")
        assert isinstance(distance, int)
        assert distance > 0

    def test_zone_coordinates_returns_lat_lng(self):
        coords = maps_client.get_zone_coordinates("GA")
        assert "lat" in coords
        assert "lng" in coords

    def test_unknown_zone_returns_defaults(self):
        coords = maps_client.get_zone_coordinates("NONEXISTENT")
        assert coords == {"lat": 0.0, "lng": 0.0}

    def test_route_total_distance_positive(self):
        route = ["GA", "MC", "ST"]
        total = maps_client.get_route_total_distance(route)
        assert total > 0

    def test_route_waypoints_length(self):
        route = ["GA", "MC", "ST"]
        waypoints = maps_client.get_route_waypoints(route)
        assert len(waypoints) == 3
        for wp in waypoints:
            assert "zone_id" in wp
            assert "lat" in wp

    def test_all_zones_have_coordinates(self):
        for zone_id in ZONE_REGISTRY:
            coords = maps_client.get_zone_coordinates(zone_id)
            assert coords["lat"] != 0.0 or coords["lng"] != 0.0, f"{zone_id} has no coordinates"

    def test_is_using_mock(self):
        assert maps_client.is_using_mock() is True


# ── Cloud Logging ────────────────────────────────────────────────────────────

class TestCloudLogging:
    """Tests for Cloud Logging console fallback."""

    def test_log_info_no_exception(self):
        """Verify log_info doesn't raise when called."""
        cloud_logging.log_info("test info message")

    def test_log_info_with_payload(self):
        cloud_logging.log_info("test", {"key": "value"})

    def test_log_warning_no_exception(self):
        cloud_logging.log_warning("test warning")

    def test_log_error_no_exception(self):
        cloud_logging.log_error("test error")

    def test_log_error_with_exception(self):
        cloud_logging.log_error("test", error=ValueError("boom"))

    def test_log_request_no_exception(self):
        cloud_logging.log_request("GET", "/health", 200, 1.5)

    def test_is_using_mock(self):
        assert cloud_logging.is_using_mock() is True


# ── Firebase Auth ────────────────────────────────────────────────────────────

class TestFirebaseAuth:
    """Tests for Firebase Authentication mock mode."""

    def test_mock_token_accepted(self):
        claims = firebase_auth.verify_token("mock-testuser")
        assert claims is not None
        assert claims["uid"] == "testuser"

    def test_mock_token_has_email(self):
        claims = firebase_auth.verify_token("mock-user123")
        assert "email" in claims
        assert "@mock.crowdpulse.dev" in claims["email"]

    def test_invalid_token_rejected(self):
        claims = firebase_auth.verify_token("invalid-token")
        assert claims is None

    def test_empty_token_rejected(self):
        claims = firebase_auth.verify_token("")
        assert claims is None

    def test_is_using_mock(self):
        assert firebase_auth.is_using_mock() is True
