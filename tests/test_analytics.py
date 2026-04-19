"""
tests/test_analytics.py
------------------------
Tests for the analytics dashboard endpoint.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestAnalyticsDashboard:
    def test_dashboard_returns_200(self):
        resp = client.get("/analytics/dashboard")
        assert resp.status_code == 200

    def test_dashboard_hotspots(self):
        resp = client.get("/analytics/dashboard")
        data = resp.json()
        assert "historical_hotspots" in data
        assert len(data["historical_hotspots"]) <= 5

    def test_dashboard_leaderboard_has_all_zones(self):
        resp = client.get("/analytics/dashboard")
        lb = resp.json()["live_leaderboard"]
        assert len(lb) > 0

    def test_dashboard_leaderboard_structure(self):
        resp = client.get("/analytics/dashboard")
        entry = resp.json()["live_leaderboard"][0]
        assert "zone_id" in entry
        assert "name" in entry
        assert "current_density" in entry
        assert "status" in entry

    def test_dashboard_recommended_entry_is_string(self):
        resp = client.get("/analytics/dashboard")
        assert isinstance(resp.json()["recommended_entry"], str)

    def test_dashboard_ai_recommendations(self):
        resp = client.get("/analytics/dashboard")
        data = resp.json()
        assert "ai_recommendations" in data
        assert isinstance(data["ai_recommendations"], list)
        assert len(data["ai_recommendations"]) >= 1

    def test_dashboard_operational_briefing(self):
        resp = client.get("/analytics/dashboard")
        data = resp.json()
        assert "operational_briefing" in data
        assert isinstance(data["operational_briefing"], str)
        assert len(data["operational_briefing"]) > 10

    def test_dashboard_has_timestamp(self):
        resp = client.get("/analytics/dashboard")
        assert "timestamp" in resp.json()

    def test_dashboard_leaderboard_sorted_descending(self):
        resp = client.get("/analytics/dashboard")
        lb = resp.json()["live_leaderboard"]
        densities = [z["current_density"] for z in lb]
        assert densities == sorted(densities, reverse=True)

    def test_dashboard_status_values_valid(self):
        resp = client.get("/analytics/dashboard")
        for entry in resp.json()["live_leaderboard"]:
            assert entry["status"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
