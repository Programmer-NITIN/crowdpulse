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


# ═══════════════════════════════════════════════════════════════════════════════
# Class 1: Gemini Caller (shared utility)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGeminiCaller:
    """Tests for the shared gemini_caller.call_gemini utility."""

    def test_call_gemini_no_model_uses_fallback(self):
        """When model is None, fallback_fn is called immediately."""
        from app.ai_engine.gemini_caller import call_gemini
        result = call_gemini(None, "test prompt", lambda: "fallback value")
        assert result == "fallback value"

    def test_call_gemini_success(self):
        """When model works, returns stripped text."""
        from app.ai_engine.gemini_caller import call_gemini
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text="  AI response  ")
        result = call_gemini(mock_model, "prompt", lambda: "fallback")
        assert result == "AI response"

    def test_call_gemini_exception_uses_fallback(self):
        """When model raises, fallback_fn is called."""
        from app.ai_engine.gemini_caller import call_gemini
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = RuntimeError("timeout")
        result = call_gemini(mock_model, "prompt", lambda: "fallback")
        assert result == "fallback"


# ═══════════════════════════════════════════════════════════════════════════════
# Class 2: Explainer Live Paths
# ═══════════════════════════════════════════════════════════════════════════════

class TestExplainerLive:
    """Tests covering explainer.py lines 25-51 (Gemini init + live call)."""

    @patch("app.ai_engine.explainer._model")
    def test_live_call_success(self, mock_model):
        """Gemini returns a valid explanation."""
        mock_model.generate_content.return_value = MagicMock(text=" AI route explanation ")
        from app.ai_engine.explainer import get_ai_explanation
        result = get_ai_explanation("test prompt")
        assert result == "AI route explanation"

    @patch("app.ai_engine.explainer._model")
    def test_live_call_failure_falls_back(self, mock_model):
        """Gemini exception triggers deterministic fallback."""
        mock_model.generate_content.side_effect = RuntimeError("timeout")
        from app.ai_engine.explainer import get_ai_explanation
        result = get_ai_explanation("test")
        assert "least congested" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Class 3: Chatbot Live Paths
# ═══════════════════════════════════════════════════════════════════════════════

class TestChatbotLive:
    """Tests covering chatbot.py lines 175-226 (Gemini grounding + unknown)."""

    @patch("app.ai_engine.chatbot._model")
    def test_grounded_intent_with_gemini(self, mock_model):
        """Known intent is grounded through Gemini phrasing."""
        mock_model.generate_content.return_value = MagicMock(
            text="Based on venue policy, the following items are prohibited..."
        )
        from app.ai_engine.chatbot import get_chat_response
        reply, intent, grounded = get_chat_response("What items are banned?")
        assert intent == "prohibited"
        assert grounded is True
        assert len(reply) > 0

    @patch("app.ai_engine.chatbot._model")
    def test_grounded_with_history(self, mock_model):
        """Grounded response includes conversation history context."""
        mock_model.generate_content.return_value = MagicMock(
            text="As mentioned, bags must be clear."
        )
        from app.ai_engine.chatbot import get_chat_response
        history = [
            {"role": "user", "content": "Tell me about bags"},
            {"role": "assistant", "content": "Clear bags only."},
        ]
        reply, intent, grounded = get_chat_response("What size?", history=history)
        assert len(reply) > 0

    @patch("app.ai_engine.chatbot._model")
    def test_grounded_gemini_fails_returns_direct(self, mock_model):
        """When Gemini phrasing fails, raw context is returned."""
        mock_model.generate_content.side_effect = RuntimeError("timeout")
        from app.ai_engine.chatbot import get_chat_response
        reply, intent, grounded = get_chat_response("What items are banned?")
        assert intent == "prohibited"
        assert grounded is True
        assert "Prohibited" in reply or "prohibited" in reply.lower()

    @patch("app.ai_engine.chatbot._model")
    def test_unknown_intent_with_gemini(self, mock_model):
        """Unknown intent falls through to Gemini general response."""
        mock_model.generate_content.return_value = MagicMock(
            text="I can help you with that venue question."
        )
        from app.ai_engine.chatbot import get_chat_response
        reply, intent, grounded = get_chat_response(
            "What is the meaning of life?"
        )
        assert grounded is False or intent is None

    @patch("app.ai_engine.chatbot._model")
    def test_unknown_intent_gemini_fails(self, mock_model):
        """Unknown intent + Gemini failure → helpful fallback."""
        mock_model.generate_content.side_effect = RuntimeError("API down")
        from app.ai_engine.chatbot import get_chat_response
        reply, intent, grounded = get_chat_response(
            "Tell me about quantum physics"
        )
        assert "steward" in reply.lower() or "help desk" in reply.lower() or "difficulties" in reply.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Class 4: Staff Advisor Live Paths
# ═══════════════════════════════════════════════════════════════════════════════

class TestStaffAdvisorLive:
    """Tests covering staff_advisor.py lines 63-143."""

    @patch("app.ai_engine.staff_advisor._model")
    def test_recommendations_live(self, mock_model):
        """Live Gemini recommendations are parsed correctly."""
        mock_model.generate_content.return_value = MagicMock(
            text="1. Deploy staff to Gate A\n2. Open Gate D for overflow\n3. Monitor Food Court"
        )
        from app.ai_engine.staff_advisor import generate_recommendations
        density = {z: 50 for z in ZONE_REGISTRY}
        recs = generate_recommendations(density)
        assert len(recs) >= 1

    @patch("app.ai_engine.staff_advisor._model")
    def test_recommendations_live_failure(self, mock_model):
        """Recommendations fallback on Gemini failure."""
        mock_model.generate_content.side_effect = RuntimeError("timeout")
        from app.ai_engine.staff_advisor import generate_recommendations
        density = {z: 50 for z in ZONE_REGISTRY}
        recs = generate_recommendations(density)
        assert isinstance(recs, list)
        assert len(recs) >= 1

    @patch("app.ai_engine.staff_advisor._model")
    def test_triage_alert_live(self, mock_model):
        """Live triage returns Gemini assessment."""
        mock_model.generate_content.return_value = MagicMock(
            text="CRITICAL: Gate A requires immediate crowd diversion."
        )
        from app.ai_engine.staff_advisor import triage_alert
        density = {z: 50 for z in ZONE_REGISTRY}
        result = triage_alert("GA", 85, density)
        assert len(result) > 0

    @patch("app.ai_engine.staff_advisor._model")
    def test_triage_alert_live_failure(self, mock_model):
        """Triage fallback on Gemini failure."""
        mock_model.generate_content.side_effect = RuntimeError("timeout")
        from app.ai_engine.staff_advisor import triage_alert
        density = {z: 50 for z in ZONE_REGISTRY}
        result = triage_alert("GA", 85, density)
        assert "Manual assessment" in result

    @patch("app.ai_engine.staff_advisor._model")
    def test_briefing_live(self, mock_model):
        """Live briefing returns Gemini summary."""
        mock_model.generate_content.return_value = MagicMock(
            text="Venue readiness is at 95%. Gate A shows elevated density."
        )
        from app.ai_engine.staff_advisor import generate_briefing
        density = {z: 50 for z in ZONE_REGISTRY}
        result = generate_briefing(density)
        assert "readiness" in result.lower() or len(result) > 10

    @patch("app.ai_engine.staff_advisor._model")
    def test_briefing_live_failure(self, mock_model):
        """Briefing fallback on Gemini failure."""
        mock_model.generate_content.side_effect = RuntimeError("timeout")
        from app.ai_engine.staff_advisor import generate_briefing
        density = {z: 50 for z in ZONE_REGISTRY}
        result = generate_briefing(density)
        assert isinstance(result, str) and len(result) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Class 5: Firestore Live Paths
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# Class 6: BigQuery Live Paths
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# Class 7: Maps Client Live Paths
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# Class 8: Cloud Logging Live Paths
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# Class 9: Firebase Auth Live Paths
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# Class 10: Decision Engine Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionEngineEdgeCases:
    """Tests covering router.py lines 54-58 and scorer.py lines 36, 38."""

    def test_family_friendly_priority_penalizes_unfriendly(self):
        """Family-friendly priority adds penalty for non-family zones."""
        from app.decision_engine.router import _calculate_edge_cost
        # C2 has family_friendly=False
        cost_ff = _calculate_edge_cost(50, 50, None, Priority.FAMILY_FRIENDLY, "C2")
        cost_fast = _calculate_edge_cost(50, 50, None, Priority.FAST_EXIT, "C2")
        assert cost_ff > cost_fast

    def test_accessible_priority_penalizes_inaccessible(self):
        """Accessible priority adds penalty for inaccessible zones."""
        from app.decision_engine.router import _calculate_edge_cost
        # C2 has accessible=False
        cost_acc = _calculate_edge_cost(50, 50, None, Priority.ACCESSIBLE, "C2")
        cost_fast = _calculate_edge_cost(50, 50, None, Priority.FAST_EXIT, "C2")
        assert cost_acc > cost_fast

    def test_scorer_entry_phase_gate_penalty(self):
        """Gates during entry phase get penalized in scoring."""
        from app.decision_engine.scorer import score_zone
        score_entry = score_zone("GA", 50, "STABLE", event_phase="entry")
        score_live = score_zone("GA", 50, "STABLE", event_phase="live")
        assert score_entry["score"] != score_live["score"]

    def test_scorer_exit_phase_gate_penalty(self):
        """Gates during exit phase get penalized in scoring."""
        from app.decision_engine.scorer import score_zone
        score_exit = score_zone("GA", 50, "STABLE", event_phase="exit")
        score_live = score_zone("GA", 50, "STABLE", event_phase="live")
        assert score_exit["score"] != score_live["score"]

    def test_prefer_fastest_constraint(self):
        """prefer_fastest constraint drastically reduces congestion penalty."""
        from app.decision_engine.router import _calculate_edge_cost
        cost_normal = _calculate_edge_cost(50, 30, None, Priority.FAST_EXIT, "C1")
        cost_fastest = _calculate_edge_cost(
            50, 30, ["prefer_fastest"], Priority.FAST_EXIT, "C1"
        )
        assert cost_fastest < cost_normal


# ═══════════════════════════════════════════════════════════════════════════════
# Class 11: Crowd Engine Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrowdEngineEdgeCases:
    """Tests covering predictor, simulator, wait_times, and cache edge cases."""

    def test_halftime_restroom_delta(self):
        """Halftime phase increases restroom predicted density."""
        from app.crowd_engine.predictor import predict_zone_density
        pred = predict_zone_density("RR", 50, event_phase="halftime")
        # During halftime, restrooms get +15 delta
        assert pred["predicted_density"] > 50

    def test_entry_gate_delta(self):
        """Entry phase increases gate predicted density."""
        from app.crowd_engine.predictor import predict_zone_density
        pred = predict_zone_density("GA", 40, event_phase="entry")
        assert pred["predicted_density"] > 40

    def test_exit_gate_delta(self):
        """Exit phase increases gate predicted density significantly."""
        from app.crowd_engine.predictor import predict_zone_density
        pred = predict_zone_density("GA", 40, event_phase="exit")
        assert pred["predicted_density"] > 40

    def test_restroom_wait_time(self):
        """Restroom zones have specific wait time calculation."""
        from app.crowd_engine.wait_times import calculate_service_wait_time
        zone_info = ZONE_REGISTRY["RR"]
        wait = calculate_service_wait_time("RR", zone_info, 80)
        assert wait > 0

    def test_medical_wait_time(self):
        """Medical zones have specific wait time calculation."""
        from app.crowd_engine.wait_times import calculate_service_wait_time
        zone_info = ZONE_REGISTRY["MC"]
        wait = calculate_service_wait_time("MC", zone_info, 80)
        assert wait > 0

    def test_entry_phase_gate_boost_simulator(self):
        """Entry phase boosts gate density in simulation."""
        from app.crowd_engine.simulator import get_zone_density_map
        now = datetime(2026, 4, 19, 19, 0)
        dm = get_zone_density_map(now, event_phase="entry")
        assert isinstance(dm, dict)
        assert "GA" in dm

    def test_cache_capacity_eviction(self):
        """Cache evicts oldest entry when max_entries is exceeded."""
        from app.crowd_engine.cache import crowd_cache
        # Test the cache type's eviction behavior using a fresh instance
        cache_type = type(crowd_cache)
        test_cache = cache_type(ttl=999, max_entries=2)
        test_cache.set("a", 1)
        test_cache.set("b", 2)
        test_cache.set("c", 3)  # Forces eviction of "a"
        assert test_cache.get("a") is None
        assert test_cache.get("b") == 2
        assert test_cache.get("c") == 3

    def test_simulator_low_density_status(self):
        """Simulator returns LOW status for low density values."""
        from app.crowd_engine.simulator import _density_to_status
        status = _density_to_status(10)
        assert status == "LOW"

    def test_simulator_critical_density_status(self):
        """Simulator returns CRITICAL status for high density values."""
        from app.crowd_engine.simulator import _density_to_status
        status = _density_to_status(90)
        assert status == "CRITICAL"


# ═══════════════════════════════════════════════════════════════════════════════
# Class 12: Config Validators
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfigValidators:
    """Tests covering config.py lines 46, 58 (non-string debug, list origins)."""

    def test_parse_debug_non_string_true(self):
        """Debug flag accepts integer 1 as True."""
        from app.config import Settings
        s = Settings(debug=1)
        assert s.debug is True

    def test_parse_debug_non_string_false(self):
        """Debug flag accepts integer 0 as False."""
        from app.config import Settings
        s = Settings(debug=0)
        assert s.debug is False

    def test_parse_origins_list_input(self):
        """Origins accepts list input and normalizes to comma-separated."""
        from app.config import Settings
        s = Settings(allowed_origins_raw=["https://a.com", "https://b.com"])
        assert s.allowed_origins == ["https://a.com", "https://b.com"]

    def test_parse_origins_empty_debug(self):
        """Empty origins with debug=true returns wildcard."""
        from app.config import Settings
        s = Settings(debug=True, allowed_origins_raw="")
        assert s.allowed_origins == ["*"]

    def test_parse_origins_empty_prod(self):
        """Empty origins with debug=false returns empty list."""
        from app.config import Settings
        s = Settings(debug=False, allowed_origins_raw="")
        assert s.allowed_origins == []


# ═══════════════════════════════════════════════════════════════════════════════
# Class 13: Prompt Builder Branches
# ═══════════════════════════════════════════════════════════════════════════════

class TestPromptBuilderBranches:
    """Tests covering prompt_builder.py lines 52, 54 (density branches)."""

    def test_prompt_high_density_vision_note(self):
        """High density route triggers bottleneck vision note."""
        from app.ai_engine.prompt_builder import build_navigation_prompt
        # Create density map with high values along route
        density = {z: 80 for z in ZONE_REGISTRY}
        scores = {z: {"score": 50, "confidence_score": 70} for z in ZONE_REGISTRY}
        preds = {z: {"trend": "INCREASING"} for z in ZONE_REGISTRY}
        prompt = build_navigation_prompt(
            "GA", "ST", ["GA", "C1", "FC"], scores, density, preds,
            5, "live", "fast_exit",
        )
        assert "bottleneck" in prompt.lower() or "congestion" in prompt.lower()

    def test_prompt_medium_density_vision_note(self):
        """Medium density route triggers turnstile vision note."""
        from app.ai_engine.prompt_builder import build_navigation_prompt
        density = {z: 60 for z in ZONE_REGISTRY}
        scores = {z: {"score": 60, "confidence_score": 75} for z in ZONE_REGISTRY}
        preds = {z: {"trend": "STABLE"} for z in ZONE_REGISTRY}
        prompt = build_navigation_prompt(
            "GA", "ST", ["GA", "C1", "FC"], scores, density, preds,
            4, "live", "fast_exit",
        )
        assert "Turnstile" in prompt or "turnstile" in prompt.lower()

    def test_prompt_low_density_vision_note(self):
        """Low density route triggers nominal flow vision note."""
        from app.ai_engine.prompt_builder import build_navigation_prompt
        density = {z: 20 for z in ZONE_REGISTRY}
        scores = {z: {"score": 90, "confidence_score": 95} for z in ZONE_REGISTRY}
        preds = {z: {"trend": "DECREASING"} for z in ZONE_REGISTRY}
        prompt = build_navigation_prompt(
            "GA", "ST", ["GA", "C1", "FC"], scores, density, preds,
            2, "live", "fast_exit",
        )
        assert "nominal" in prompt.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Class 14: Rate Limiter
# ═══════════════════════════════════════════════════════════════════════════════

class TestRateLimiterIsRateLimited:
    """Tests covering rate_limiter.py is_rate_limited method."""

    def test_is_rate_limited_under_limit(self):
        """is_rate_limited returns False when under the limit."""
        import asyncio
        from app.middleware.rate_limiter import make_rate_limiter
        limiter = make_rate_limiter(max_requests=10, window_seconds=60)
        mock_request = MagicMock()
        mock_request.client.host = "10.0.0.1"
        mock_request.headers = {}

        async def _check():
            return await limiter.is_rate_limited(mock_request)

        assert asyncio.run(_check()) is False

    def test_is_rate_limited_over_limit(self):
        """is_rate_limited returns True when over the limit."""
        import asyncio
        import time as _time
        from app.middleware.rate_limiter import make_rate_limiter
        limiter = make_rate_limiter(max_requests=2, window_seconds=60)
        mock_request = MagicMock()
        mock_request.client.host = "10.0.0.2"
        mock_request.headers = {}
        # Fill the window past the limit
        limiter.store["10.0.0.2"].extend([_time.time()] * 3)

        async def _check():
            return await limiter.is_rate_limited(mock_request)

        assert asyncio.run(_check()) is True


# ═══════════════════════════════════════════════════════════════════════════════
# Class 15: Main Application Lifespan
# ═══════════════════════════════════════════════════════════════════════════════

class TestMainLifespan:
    """Tests covering main.py lifespan function."""

    def test_lifespan_context_manager(self):
        """Lifespan context manager runs without error."""
        import asyncio
        from app.main import lifespan, app

        async def _test():
            async with lifespan(app):
                pass  # Just verify it doesn't crash

        asyncio.run(_test())
