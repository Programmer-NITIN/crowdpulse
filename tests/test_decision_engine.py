"""
tests/test_decision_engine.py
------------------------------
Unit tests for the decision engine: scoring and Dijkstra routing.
"""

from app.decision_engine.scorer import score_zone, score_all_zones
from app.decision_engine.router import find_best_route, estimate_wait_minutes, _calculate_edge_cost
from app.config import ZONE_REGISTRY
from app.models.navigation_models import Priority


class TestScorer:
    def test_low_density_high_score(self):
        result = score_zone("GA", 10, "STABLE")
        assert result["score"] >= 80

    def test_high_density_low_score(self):
        result = score_zone("GA", 90, "STABLE")
        assert result["score"] <= 30

    def test_score_bounds(self):
        result = score_zone("GA", 50, "STABLE")
        assert 0 <= result["score"] <= 100
        assert 0 <= result["confidence_score"] <= 100

    def test_increasing_trend_lowers_score(self):
        stable = score_zone("GA", 50, "STABLE")
        increasing = score_zone("GA", 50, "INCREASING")
        assert increasing["score"] < stable["score"]

    def test_decreasing_trend_raises_score(self):
        stable = score_zone("GA", 50, "STABLE")
        decreasing = score_zone("GA", 50, "DECREASING")
        assert decreasing["score"] > stable["score"]

    def test_halftime_amenity_penalty(self):
        live = score_zone("FC", 50, "STABLE", event_phase="live")
        halftime = score_zone("FC", 50, "STABLE", event_phase="halftime")
        assert halftime["score"] < live["score"]

    def test_score_all_zones(self):
        density_map = {z: 50 for z in ZONE_REGISTRY}
        predictions = {z: {"trend": "STABLE"} for z in ZONE_REGISTRY}
        scores = score_all_zones(density_map, predictions)
        for zone_id in ZONE_REGISTRY:
            assert zone_id in scores
            assert "score" in scores[zone_id]
            assert "confidence_score" in scores[zone_id]

    def test_confidence_increases_with_decreasing_trend(self):
        result = score_zone("GA", 40, "DECREASING")
        assert result["confidence_score"] >= result["score"]


class TestRouter:
    def _make_scores(self, default_score=70):
        return {z: {"score": default_score, "confidence_score": default_score} for z in ZONE_REGISTRY}

    def test_same_source_destination(self):
        route = find_best_route("GA", "GA", self._make_scores())
        assert route == ["GA"]

    def test_direct_neighbor_route(self):
        route = find_best_route("GA", "C1", self._make_scores())
        assert route is not None
        assert route[0] == "GA"
        assert route[-1] == "C1"

    def test_multi_hop_route(self):
        route = find_best_route("GA", "ST", self._make_scores())
        assert route is not None
        assert len(route) >= 2
        assert route[0] == "GA"
        assert route[-1] == "ST"

    def test_route_avoids_congested_zones(self):
        scores = self._make_scores(default_score=70)
        scores["C2"] = {"score": 5, "confidence_score": 5}
        route = find_best_route("GA", "ST", scores)
        assert route is not None

    def test_no_path_returns_none(self):
        scores = {"ISOLATED": {"score": 50, "confidence_score": 50}}
        route = find_best_route("ISOLATED", "GA", scores)
        assert route is None

    def test_accessible_priority_avoids_inaccessible(self):
        scores = self._make_scores(70)
        route_normal = find_best_route("GA", "ST", scores, priority=Priority.FAST_EXIT)
        route_access = find_best_route("GA", "ST", scores, priority=Priority.ACCESSIBLE)
        assert route_normal is not None
        assert route_access is not None

    def test_estimate_wait_minutes(self):
        density_map = {z: 50 for z in ZONE_REGISTRY}
        route = ["GA", "C1", "FC"]
        wait = estimate_wait_minutes(route, density_map)
        assert wait > 0

    def test_estimate_wait_high_density(self):
        density_map = {z: 80 for z in ZONE_REGISTRY}
        route = ["GA", "C1", "FC"]
        wait_high = estimate_wait_minutes(route, density_map)
        density_map_low = {z: 20 for z in ZONE_REGISTRY}
        wait_low = estimate_wait_minutes(route, density_map_low)
        assert wait_high > wait_low

    def test_edge_cost_low_crowd_amplifies_penalty(self):
        cost_fast = _calculate_edge_cost(50, 30, None, Priority.FAST_EXIT, "C1")
        cost_low = _calculate_edge_cost(50, 30, None, Priority.LOW_CROWD, "C1")
        assert cost_low > cost_fast

    def test_edge_cost_avoid_crowd_constraint(self):
        cost_normal = _calculate_edge_cost(50, 30, None, Priority.FAST_EXIT, "C1")
        cost_avoid = _calculate_edge_cost(50, 30, ["avoid_crowd"], Priority.FAST_EXIT, "C1")
        assert cost_avoid > cost_normal

    def test_trend_penalty_increasing(self):
        cost_stable = _calculate_edge_cost(50, 50, None, Priority.FAST_EXIT, "C1", "STABLE")
        cost_inc = _calculate_edge_cost(50, 50, None, Priority.FAST_EXIT, "C1", "INCREASING")
        assert cost_inc > cost_stable

    def test_route_ga_to_ms(self):
        route = find_best_route("GA", "MS", self._make_scores())
        assert route is not None
        assert route[0] == "GA"
        assert route[-1] == "MS"

    def test_route_rr_to_fc(self):
        route = find_best_route("RR", "FC", self._make_scores())
        assert route is not None
        assert len(route) >= 3

    def test_route_mc_to_gd(self):
        route = find_best_route("MC", "GD", self._make_scores())
        assert route is not None
