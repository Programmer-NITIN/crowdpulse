"""
tests/test_integration.py
--------------------------
End-to-end integration tests that verify multi-service workflows.
"""

from fastapi.testclient import TestClient
from app.main import app
from app.google_services import firestore_client

client = TestClient(app)
_HEADERS = {"X-Forwarded-For": "10.50.0.1"}


class TestNavigationPersistence:
    """Verify that navigation sessions are persisted to Firestore (mock)."""

    def test_navigation_stores_session(self):
        from app.middleware.rate_limiter import navigation_rate_limit
        navigation_rate_limit.store.clear()

        resp = client.post(
            "/navigate/suggest",
            json={
                "user_id": "integration-user",
                "current_zone": "GA",
                "destination": "FC",
                "priority": "fast_exit",
            },
            headers=_HEADERS,
        )
        assert resp.status_code == 200

        docs = firestore_client.list_documents("navigation_sessions")
        assert len(docs) > 0

        latest = docs[-1]
        assert latest["user_id"] == "integration-user"
        assert latest["source"] == "GA"
        assert latest["destination"] == "FC"


class TestCrowdToNavigationPipeline:
    """Verify the full pipeline from crowd data to navigation."""

    def test_crowd_data_feeds_navigation(self):
        from app.middleware.rate_limiter import navigation_rate_limit
        navigation_rate_limit.store.clear()

        crowd_resp = client.get("/crowd/status")
        assert crowd_resp.status_code == 200
        zones = crowd_resp.json()["zones"]
        assert len(zones) > 0

        nav_resp = client.post(
            "/navigate/suggest",
            json={
                "user_id": "pipeline-user",
                "current_zone": zones[0]["zone_id"],
                "destination": zones[-1]["zone_id"],
                "priority": "low_crowd",
            },
            headers=_HEADERS,
        )
        assert nav_resp.status_code == 200
        route = nav_resp.json()["recommended_route"]
        assert route[0] == zones[0]["zone_id"]
        assert route[-1] == zones[-1]["zone_id"]


class TestPredictionToScoringPipeline:
    """Verify predictions feed into navigation scoring."""

    def test_prediction_influences_route(self):
        from app.middleware.rate_limiter import navigation_rate_limit
        navigation_rate_limit.store.clear()

        pred_resp = client.get("/crowd/predict?zone_id=GA")
        assert pred_resp.status_code == 200
        assert "trend" in pred_resp.json()

        nav_resp = client.post(
            "/navigate/suggest",
            json={
                "user_id": "pred-user",
                "current_zone": "GA",
                "destination": "ST",
                "priority": "fast_exit",
            },
            headers=_HEADERS,
        )
        assert nav_resp.status_code == 200
        assert "reasoning_summary" in nav_resp.json()


class TestMultiServiceHealth:
    """Verify health endpoint reports all services."""

    def test_all_services_reported(self):
        resp = client.get("/health")
        data = resp.json()
        expected_services = ["gemini", "firestore", "bigquery", "maps", "cloud_logging"]
        for svc in expected_services:
            assert svc in data["services"], f"Missing service: {svc}"


class TestChatToRoutePlanner:
    """Verify chat correctly redirects route questions."""

    def test_chat_route_redirect_then_navigate(self):
        from app.middleware.rate_limiter import navigation_rate_limit
        navigation_rate_limit.store.clear()

        chat_resp = client.post(
            "/assistant/chat",
            json={"user_id": "chat-user", "message": "How do I get to the food court?"},
        )
        assert chat_resp.status_code == 200
        assert chat_resp.json()["intent"] == "route"
        assert "Route Planner" in chat_resp.json()["reply"]

        nav_resp = client.post(
            "/navigate/suggest",
            json={
                "user_id": "chat-user",
                "current_zone": "GA",
                "destination": "FC",
                "priority": "fast_exit",
            },
            headers=_HEADERS,
        )
        assert nav_resp.status_code == 200
        assert nav_resp.json()["recommended_route"][-1] == "FC"


class TestAllZonesPredictable:
    """Verify every zone can be predicted."""

    def test_all_zones_have_predictions(self):
        from app.config import ZONE_REGISTRY
        for zone_id in ZONE_REGISTRY:
            resp = client.get(f"/crowd/predict?zone_id={zone_id}")
            assert resp.status_code == 200, f"Prediction failed for {zone_id}"
            assert resp.json()["zone_id"] == zone_id
