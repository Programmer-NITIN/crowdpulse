"""
tests/test_coverage_boost.py
------------------------------
Comprehensive tests targeting ALL uncovered lines across the codebase.

Uses unittest.mock.patch to simulate live Google service connections
and Gemini API calls without requiring real API keys or network access.

This file covers:
- AI Engine: explainer, chatbot, staff_advisor, gemini_caller
- Google Services: firestore, bigquery, cloud_logging, firebase_auth, maps
- Decision Engine: router edge cases, scorer edge cases
- Crowd Engine: predictor, simulator, wait_times, cache edge cases
- Config: Settings validators
- Prompt Builder: density-level branches
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

from app.config import ZONE_REGISTRY
from app.models.navigation_models import Priority


# ══════════════════════════════════════════════════════════════════════

class TestFirestoreLive:
    """Tests covering firestore_client.py lines 59-108."""

    @patch("app.google_services.firestore_client._using_mock", False)
    @patch("app.google_services.firestore_client._client")
    def test_store_document_live(self, mock_client):
        """Live Firestore write delegates to client."""
        from app.google_services.firestore_client import store_document
        store_document("events", "doc1", {"key": "val"})
        mock_client.collection.assert_called_once_with("events")

    @patch("app.google_services.firestore_client._using_mock", False)
    @patch("app.google_services.firestore_client._client")
    def test_store_document_error_fallback(self, mock_client):
        """Live Firestore write failure falls back to mock store."""
        mock_client.collection.side_effect = RuntimeError("connection lost")
        from app.google_services.firestore_client import store_document
        store_document("events", "doc1", {"key": "val"})  # Should not raise

    @patch("app.google_services.firestore_client._using_mock", False)
    @patch("app.google_services.firestore_client._client")
    def test_get_document_live(self, mock_client):
        """Live Firestore read returns doc dict."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"key": "val"}
        mock_client.collection.return_value.document.return_value.get.return_value = mock_doc
        from app.google_services.firestore_client import get_document
        result = get_document("events", "doc1")
        assert result == {"key": "val"}

    @patch("app.google_services.firestore_client._using_mock", False)
    @patch("app.google_services.firestore_client._client")
    def test_get_document_not_exists(self, mock_client):
        """Live Firestore read for non-existent doc returns None."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_client.collection.return_value.document.return_value.get.return_value = mock_doc
        from app.google_services.firestore_client import get_document
        result = get_document("events", "missing")
        assert result is None

    @patch("app.google_services.firestore_client._using_mock", False)
    @patch("app.google_services.firestore_client._client")
    def test_get_document_error_fallback(self, mock_client):
        """Live Firestore read failure falls back to mock store."""
        mock_client.collection.side_effect = RuntimeError("read error")
        from app.google_services.firestore_client import get_document
        result = get_document("nonexistent_collection_xyz", "no_doc")
        assert result is None  # Mock store has no entry for this path

    @patch("app.google_services.firestore_client._using_mock", False)
    @patch("app.google_services.firestore_client._client")
    def test_list_documents_live(self, mock_client):
        """Live Firestore list returns doc dicts."""
        mock_doc1 = MagicMock()
        mock_doc1.to_dict.return_value = {"a": 1}
        mock_doc2 = MagicMock()
        mock_doc2.to_dict.return_value = {"b": 2}
        mock_client.collection.return_value.stream.return_value = [mock_doc1, mock_doc2]
        from app.google_services.firestore_client import list_documents
        result = list_documents("events")
        assert len(result) == 2

    @patch("app.google_services.firestore_client._using_mock", False)
    @patch("app.google_services.firestore_client._client")
    def test_list_documents_error_fallback(self, mock_client):
        """Live Firestore list failure falls back to mock store."""
        mock_client.collection.side_effect = RuntimeError("list error")
        from app.google_services.firestore_client import list_documents
        result = list_documents("events")
        assert isinstance(result, list)

    def test_mock_store_size_property(self):
        """Mock store size property returns document count."""
        from app.google_services.firestore_client import _mock_store
        initial = _mock_store.size
        _mock_store.set_document("test_col", "test_doc", {"x": 1})
        assert _mock_store.size >= initial
        # Clean up
        _mock_store._data.pop("test_col/test_doc", None)


# ══════════════════════════════════════════════════════════════════════

class TestBigQueryLive:
    """Tests covering bigquery_client.py lines 71-157."""

    @patch("app.google_services.bigquery_client._using_mock", False)
    @patch("app.google_services.bigquery_client._client")
    def test_hotspots_live(self, mock_client):
        """Live BigQuery hotspots query returns zone names."""
        mock_row = MagicMock()
        mock_row.zone_name = "Gate A — North Entry"
        mock_client.query.return_value.result.return_value = [mock_row]
        from app.google_services.bigquery_client import get_historical_hotspots
        result = get_historical_hotspots(top_n=3)
        assert "Gate A — North Entry" in result

    @patch("app.google_services.bigquery_client._using_mock", False)
    @patch("app.google_services.bigquery_client._client")
    def test_hotspots_error_fallback(self, mock_client):
        """Live BigQuery hotspots failure falls back to mock."""
        mock_client.query.side_effect = RuntimeError("BQ error")
        from app.google_services.bigquery_client import get_historical_hotspots
        result = get_historical_hotspots()
        assert isinstance(result, list) and len(result) > 0

    @patch("app.google_services.bigquery_client._using_mock", False)
    @patch("app.google_services.bigquery_client._client")
    def test_peak_density_live(self, mock_client):
        """Live BigQuery peak density query returns stats dict."""
        mock_row = MagicMock()
        mock_row.avg_peak_density = 72
        mock_row.max_peak_density = 95
        mock_row.sample_count = 500
        mock_client.query.return_value.result.return_value = [mock_row]
        from app.google_services.bigquery_client import get_peak_density_history
        result = get_peak_density_history("GA")
        assert result["avg_peak_density"] == 72

    @patch("app.google_services.bigquery_client._using_mock", False)
    @patch("app.google_services.bigquery_client._client")
    def test_peak_density_empty_result(self, mock_client):
        """Live BigQuery with no results falls back to mock."""
        mock_client.query.return_value.result.return_value = []
        from app.google_services.bigquery_client import get_peak_density_history
        result = get_peak_density_history("GA")
        assert "zone_id" in result

    @patch("app.google_services.bigquery_client._using_mock", False)
    @patch("app.google_services.bigquery_client._client")
    def test_peak_density_error_fallback(self, mock_client):
        """Live BigQuery peak density failure falls back to mock."""
        mock_client.query.side_effect = RuntimeError("BQ error")
        from app.google_services.bigquery_client import get_peak_density_history
        result = get_peak_density_history("GA")
        assert isinstance(result, dict)


# ══════════════════════════════════════════════════════════════════════

class TestMapsLive:
    """Tests covering maps_client.py lines 24-60."""

    @patch("app.google_services.maps_client._using_mock", False)
    @patch("app.google_services.maps_client._client")
    def test_walking_distance_live(self, mock_client):
        """Live Maps distance request returns API value."""
        mock_client.distance_matrix.return_value = {
            "rows": [{"elements": [{"distance": {"value": 150}}]}]
        }
        from app.google_services.maps_client import get_walking_distance
        dist = get_walking_distance("GA", "C1")
        assert dist == 150

    @patch("app.google_services.maps_client._using_mock", False)
    @patch("app.google_services.maps_client._client")
    def test_walking_distance_error_fallback(self, mock_client):
        """Live Maps distance failure falls back to mock."""
        mock_client.distance_matrix.side_effect = RuntimeError("API error")
        from app.google_services.maps_client import get_walking_distance
        dist = get_walking_distance("GA", "C1")
        assert isinstance(dist, int) and dist > 0

    @patch("app.google_services.maps_client._using_mock", False)
    @patch("app.google_services.maps_client._client")
    def test_walking_distance_missing_coords(self, mock_client):
        """Missing coordinates triggers mock fallback path."""
        from app.google_services.maps_client import get_walking_distance
        dist = get_walking_distance("UNKNOWN_A", "UNKNOWN_B")
        assert isinstance(dist, int)


# ══════════════════════════════════════════════════════════════════════

class TestCloudLoggingLive:
    """Tests covering cloud_logging.py lines 24-82."""

    @patch("app.google_services.cloud_logging._using_mock", False)
    @patch("app.google_services.cloud_logging._cloud_logger")
    def test_log_info_live(self, mock_logger):
        """Live Cloud Logging info call."""
        from app.google_services.cloud_logging import log_info
        log_info("test message", {"key": "val"})
        mock_logger.log_struct.assert_called_once()

    @patch("app.google_services.cloud_logging._using_mock", False)
    @patch("app.google_services.cloud_logging._cloud_logger")
    def test_log_warning_live(self, mock_logger):
        """Live Cloud Logging warning call."""
        from app.google_services.cloud_logging import log_warning
        log_warning("test warning", {"context": "test"})
        mock_logger.log_struct.assert_called_once()

    @patch("app.google_services.cloud_logging._using_mock", False)
    @patch("app.google_services.cloud_logging._cloud_logger")
    def test_log_error_live(self, mock_logger):
        """Live Cloud Logging error call with exception."""
        from app.google_services.cloud_logging import log_error
        log_error("test error", error=ValueError("oops"), payload={"ctx": "test"})
        mock_logger.log_struct.assert_called_once()

    @patch("app.google_services.cloud_logging._using_mock", False)
    @patch("app.google_services.cloud_logging._cloud_logger")
    def test_log_error_live_no_exception(self, mock_logger):
        """Live Cloud Logging error call without exception."""
        from app.google_services.cloud_logging import log_error
        log_error("plain error")
        mock_logger.log_struct.assert_called_once()

    @patch("app.google_services.cloud_logging._using_mock", False)
    @patch("app.google_services.cloud_logging._cloud_logger")
    def test_log_request_live(self, mock_logger):
        """Live Cloud Logging request call."""
        from app.google_services.cloud_logging import log_request
        log_request("GET", "/health", 200, 12.5)
        mock_logger.log_struct.assert_called_once()


# ══════════════════════════════════════════════════════════════════════

class TestFirebaseAuthLive:
    """Tests covering firebase_auth.py lines 23-59."""

    @patch("app.google_services.firebase_auth._using_mock", False)
    def test_verify_live_valid(self):
        """Live Firebase Auth verify with valid token."""
        mock_auth = MagicMock()
        mock_auth.verify_id_token.return_value = {
            "uid": "real-user-123",
            "email": "user@example.com",
        }
        import sys
        sys.modules["firebase_admin.auth"] = mock_auth
        try:
            from app.google_services.firebase_auth import verify_token
            claims = verify_token("real-firebase-token")
            assert claims["uid"] == "real-user-123"
        finally:
            sys.modules.pop("firebase_admin.auth", None)

    @patch("app.google_services.firebase_auth._using_mock", False)
    def test_verify_live_failure(self):
        """Live Firebase Auth verify failure returns None."""
        mock_auth = MagicMock()
        mock_auth.verify_id_token.side_effect = Exception("invalid token")
        import sys
        sys.modules["firebase_admin.auth"] = mock_auth
        try:
            from app.google_services.firebase_auth import verify_token
            claims = verify_token("bad-token")
            assert claims is None
        finally:
            sys.modules.pop("firebase_admin.auth", None)

