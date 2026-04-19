"""
tests/test_performance.py
--------------------------
Performance benchmarks to verify latency and throughput targets.
"""

import time
from datetime import datetime

from fastapi.testclient import TestClient
from app.main import app
from app.crowd_engine.simulator import get_zone_density_map
from app.crowd_engine.predictor import predict_all_zones
from app.decision_engine.scorer import score_all_zones
from app.decision_engine.router import find_best_route

client = TestClient(app)


class TestAPILatency:
    def test_health_under_100ms(self):
        start = time.monotonic()
        resp = client.get("/health")
        elapsed = (time.monotonic() - start) * 1000
        assert resp.status_code == 200
        assert elapsed < 100, f"Health took {elapsed:.1f}ms"

    def test_crowd_status_under_200ms(self):
        start = time.monotonic()
        resp = client.get("/crowd/status")
        elapsed = (time.monotonic() - start) * 1000
        assert resp.status_code == 200
        assert elapsed < 200, f"Crowd status took {elapsed:.1f}ms"

    def test_navigation_under_500ms(self):
        from app.middleware.rate_limiter import navigation_rate_limit
        navigation_rate_limit.store.clear()

        start = time.monotonic()
        resp = client.post(
            "/navigate/suggest",
            json={
                "user_id": "perf-test",
                "current_zone": "GA",
                "destination": "FC",
                "priority": "fast_exit",
            },
            headers={"X-Forwarded-For": "10.99.0.1"},
        )
        elapsed = (time.monotonic() - start) * 1000
        assert resp.status_code == 200
        assert elapsed < 500, f"Navigation took {elapsed:.1f}ms"

    def test_wait_times_under_200ms(self):
        start = time.monotonic()
        resp = client.get("/crowd/wait-times")
        elapsed = (time.monotonic() - start) * 1000
        assert resp.status_code == 200
        assert elapsed < 200, f"Wait times took {elapsed:.1f}ms"


class TestEnginePerformance:
    def test_density_map_under_5ms(self):
        now = datetime(2026, 4, 19, 18, 0)
        start = time.monotonic()
        for _ in range(100):
            get_zone_density_map(now)
        avg_ms = (time.monotonic() - start) * 10
        assert avg_ms < 5, f"Density map avg {avg_ms:.2f}ms"

    def test_predictions_under_10ms(self):
        now = datetime(2026, 4, 19, 18, 0)
        start = time.monotonic()
        for _ in range(100):
            predict_all_zones(now)
        avg_ms = (time.monotonic() - start) * 10
        assert avg_ms < 10, f"Predictions avg {avg_ms:.2f}ms"

    def test_scoring_under_5ms(self):
        density_map = {z: 50 for z in get_zone_density_map()}
        predictions = {z: {"trend": "STABLE"} for z in density_map}
        start = time.monotonic()
        for _ in range(100):
            score_all_zones(density_map, predictions)
        avg_ms = (time.monotonic() - start) * 10
        assert avg_ms < 5, f"Scoring avg {avg_ms:.2f}ms"

    def test_dijkstra_under_10ms(self):
        scores = {z: {"score": 50, "confidence_score": 50} for z in get_zone_density_map()}
        from app.decision_engine.router import RouteContext
        
        start = time.perf_counter()
        for _ in range(100):
            find_best_route("GA", "ST", scores, ctx=RouteContext())
        avg_ms = (time.perf_counter() - start) * 10
        assert avg_ms < 10, f"Dijkstra avg {avg_ms:.2f}ms"


class TestThroughput:
    def test_health_throughput(self):
        start = time.monotonic()
        count = 200
        for _ in range(count):
            client.get("/health")
        elapsed = time.monotonic() - start
        rps = count / elapsed
        assert rps > 100, f"Health RPS: {rps:.0f}"

    def test_crowd_status_throughput(self):
        start = time.monotonic()
        count = 100
        for _ in range(count):
            client.get("/crowd/status")
        elapsed = time.monotonic() - start
        rps = count / elapsed
        assert rps > 50, f"Crowd status RPS: {rps:.0f}"
