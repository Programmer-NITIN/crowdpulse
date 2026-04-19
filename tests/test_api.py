"""
tests/test_api.py
-----------------
Integration tests for all API endpoints using FastAPI's TestClient.
These do NOT call real Gemini or Google services (mocks are used automatically).
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

_NAV_HEADERS = {"X-Forwarded-For": "10.203.0.1"}


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_returns_version(self):
        resp = client.get("/health")
        assert "version" in resp.json()

    def test_health_returns_services(self):
        resp = client.get("/health")
        services = resp.json()["services"]
        assert "gemini" in services
        assert "firestore" in services
        assert "bigquery" in services
        assert "maps" in services
        assert "cloud_logging" in services

    def test_health_service_values_valid(self):
        resp = client.get("/health")
        for svc, status in resp.json()["services"].items():
            assert status in ("configured", "mock", "live"), f"{svc} has invalid status: {status}"


class TestCrowdEndpoints:
    def test_crowd_status_returns_all_zones(self):
        resp = client.get("/crowd/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "zones" in data
        assert len(data["zones"]) > 0

    def test_crowd_status_zone_structure(self):
        resp = client.get("/crowd/status")
        zone = resp.json()["zones"][0]
        assert "zone_id" in zone
        assert "density" in zone
        assert "status" in zone
        assert zone["status"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_crowd_status_has_timestamp(self):
        resp = client.get("/crowd/status")
        assert "timestamp" in resp.json()

    def test_crowd_status_density_bounds(self):
        resp = client.get("/crowd/status")
        for zone in resp.json()["zones"]:
            assert 0 <= zone["density"] <= 100

    def test_crowd_predict_valid_zone(self):
        resp = client.get("/crowd/predict?zone_id=GA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["zone_id"] == "GA"
        assert "predicted_density" in data
        assert "trend" in data

    def test_crowd_predict_invalid_zone(self):
        resp = client.get("/crowd/predict?zone_id=INVALID")
        assert resp.status_code == 404

    def test_crowd_predict_food_court(self):
        resp = client.get("/crowd/predict?zone_id=FC")
        assert resp.status_code == 200

    def test_crowd_predict_trend_values(self):
        resp = client.get("/crowd/predict?zone_id=GA")
        assert resp.json()["trend"] in ("INCREASING", "STABLE", "DECREASING")

    def test_crowd_predict_prediction_window(self):
        resp = client.get("/crowd/predict?zone_id=GA")
        assert resp.json()["prediction_window_minutes"] == 30

    def test_wait_times_returns_services(self):
        resp = client.get("/crowd/wait-times")
        assert resp.status_code == 200
        data = resp.json()
        assert "services" in data
        assert len(data["services"]) > 0

    def test_wait_times_structure(self):
        resp = client.get("/crowd/wait-times")
        svc = resp.json()["services"][0]
        assert "zone_id" in svc
        assert "name" in svc
        assert "wait_minutes" in svc
        assert "trend" in svc
        assert "status" in svc

    def test_wait_times_non_negative(self):
        resp = client.get("/crowd/wait-times")
        for svc in resp.json()["services"]:
            assert svc["wait_minutes"] >= 0


class TestNavigationEndpoint:
    def _suggest(self, current="GA", dest="FC", priority="fast_exit"):
        from app.middleware.rate_limiter import navigation_rate_limit
        navigation_rate_limit.store.clear()
        return client.post(
            "/navigate/suggest",
            json={
                "user_id": "test_user",
                "current_zone": current,
                "destination": dest,
                "priority": priority,
            },
            headers=_NAV_HEADERS,
        )

    def test_suggest_returns_route(self):
        resp = self._suggest("GA", "FC")
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_route" in data
        assert len(data["recommended_route"]) > 0

    def test_suggest_route_starts_at_source(self):
        resp = self._suggest("GA", "FC")
        assert resp.json()["recommended_route"][0] == "GA"

    def test_suggest_route_ends_at_destination(self):
        resp = self._suggest("GA", "ST")
        assert resp.json()["recommended_route"][-1] == "ST"

    def test_suggest_contains_zone_scores(self):
        resp = self._suggest("GB", "FC")
        assert "zone_scores" in resp.json()

    def test_suggest_contains_ai_explanation(self):
        resp = self._suggest("GA", "FC")
        data = resp.json()
        assert "ai_explanation" in data
        assert isinstance(data["ai_explanation"], str)
        assert len(data["ai_explanation"]) > 10

    def test_suggest_invalid_source_zone(self):
        resp = self._suggest("INVALID", "FC")
        assert resp.status_code == 404

    def test_suggest_invalid_destination_zone(self):
        resp = self._suggest("GA", "NOWHERE")
        assert resp.status_code == 404

    def test_suggest_accepts_zone_names(self):
        resp = self._suggest("Gate A — North Entry", "Food Court — Level 1")
        assert resp.status_code == 200

    def test_suggest_same_source_destination(self):
        resp = self._suggest("GA", "GA")
        assert resp.status_code == 200
        assert resp.json()["recommended_route"] == ["GA"]

    def test_suggest_end_to_end_payload(self):
        resp = client.post(
            "/navigate/suggest",
            json={
                "user_id": "e2e_tester",
                "current_zone": "GA",
                "destination": "FC",
                "priority": "fast_exit",
                "constraints": ["prefer_fastest"],
                "user_note": "I just want my hotdog",
            },
            headers=_NAV_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_route" in data
        assert "ai_explanation" in data
        assert "reasoning_summary" in data
        assert "density_factor" in data["reasoning_summary"]
        assert "trend_factor" in data["reasoning_summary"]
        assert "event_factor" in data["reasoning_summary"]

    def test_suggest_returns_distance(self):
        resp = self._suggest("GA", "FC")
        data = resp.json()
        assert "total_walking_distance_meters" in data
        assert data["total_walking_distance_meters"] >= 0

    def test_suggest_returns_waypoints(self):
        resp = self._suggest("GA", "FC")
        data = resp.json()
        assert "route_waypoints" in data
        if len(data["route_waypoints"]) > 0:
            wp = data["route_waypoints"][0]
            assert "zone_id" in wp
            assert "lat" in wp
            assert "lng" in wp

    def test_suggest_returns_wait_minutes(self):
        resp = self._suggest("GA", "ST")
        data = resp.json()
        assert "estimated_wait_minutes" in data
        assert isinstance(data["estimated_wait_minutes"], int)
        assert data["estimated_wait_minutes"] >= 0

    def test_suggest_accessible_priority(self):
        resp = self._suggest("GA", "ST", priority="accessible")
        assert resp.status_code == 200
        route = resp.json()["recommended_route"]
        assert len(route) > 0

    def test_suggest_low_crowd_priority(self):
        resp = self._suggest("GA", "ST", priority="low_crowd")
        assert resp.status_code == 200


class TestChatEndpoint:
    def test_chat_returns_reply(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "What items are prohibited?"},
        )
        assert resp.status_code == 200
        assert "reply" in resp.json()

    def test_chat_returns_intent(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "What items are not allowed?"},
        )
        data = resp.json()
        assert data["intent"] == "prohibited"

    def test_chat_route_redirect(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "How do I get to the food court?"},
        )
        data = resp.json()
        assert data["intent"] == "route"
        assert "Route Planner" in data["reply"]

    def test_chat_timing_intent(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "When does the match start?"},
        )
        assert resp.json()["intent"] == "timing"

    def test_chat_accessibility_intent(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "Where are wheelchair spaces?"},
        )
        assert resp.json()["intent"] == "accessibility"

    def test_chat_bag_policy_intent(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "What is the bag policy?"},
        )
        assert resp.json()["intent"] == "bag"

    def test_chat_reentry_intent(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "Can I leave and come back?"},
        )
        assert resp.json()["intent"] == "reentry"

    def test_chat_first_aid_intent(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "Where is first aid?"},
        )
        assert resp.json()["intent"] == "first_aid"

    def test_chat_parking_intent(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "Where can I park my car?"},
        )
        assert resp.json()["intent"] == "parking"

    def test_chat_lost_property_intent(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "I lost my wallet"},
        )
        assert resp.json()["intent"] == "lost_property"

    def test_chat_weather_intent(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "What if it rains?"},
        )
        assert resp.json()["intent"] == "weather"

    def test_chat_ticket_intent(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "Do I need a digital ticket?"},
        )
        assert resp.json()["intent"] == "ticket"

    def test_chat_grounded_flag(self):
        resp = client.post(
            "/assistant/chat",
            json={"user_id": "test-user", "message": "What items are prohibited?"},
        )
        assert resp.json()["grounded"] is True


class TestAnalyticsEndpoint:
    def test_analytics_dashboard(self):
        resp = client.get("/analytics/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "historical_hotspots" in data
        assert "live_leaderboard" in data
        assert "recommended_entry" in data
        assert "ai_recommendations" in data
        assert "operational_briefing" in data

    def test_analytics_hotspots_are_strings(self):
        resp = client.get("/analytics/dashboard")
        for h in resp.json()["historical_hotspots"]:
            assert isinstance(h, str)

    def test_analytics_leaderboard_sorted(self):
        resp = client.get("/analytics/dashboard")
        lb = resp.json()["live_leaderboard"]
        densities = [z["current_density"] for z in lb]
        assert densities == sorted(densities, reverse=True)


class TestAuthEndpoint:
    def test_auth_missing_header(self):
        resp = client.get("/auth/verify")
        assert resp.status_code == 401

    def test_auth_mock_token(self):
        resp = client.get("/auth/verify", headers={"Authorization": "Bearer mock-testuser"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is True
        assert data["uid"] == "testuser"

    def test_auth_invalid_token(self):
        resp = client.get("/auth/verify", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401

    def test_auth_malformed_header(self):
        resp = client.get("/auth/verify", headers={"Authorization": "NotBearer token"})
        assert resp.status_code == 401
