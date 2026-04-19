"""
tests/test_crowd_engine.py
---------------------------
Unit tests for the crowd engine: simulator, predictor, cache, wait times.
"""

from datetime import datetime

from app.crowd_engine.cache import _TTLCache
from app.crowd_engine.simulator import (
    get_zone_density_map,
    get_zone_crowd_detail,
    _density_to_status,
    _is_peak_hour,
)
from app.crowd_engine.predictor import (
    predict_zone_density,
    predict_all_zones,
    _compute_time_delta,
    _net_trend,
)
from app.crowd_engine.wait_times import (
    calculate_service_wait_time,
    determine_wait_trend,
    get_wait_status,
)
from app.config import ZONE_REGISTRY


class TestTTLCache:
    def test_set_and_get(self):
        cache = _TTLCache(ttl=10)
        cache.set("k", "v")
        assert cache.get("k") == "v"

    def test_expired_entry_returns_none(self):
        cache = _TTLCache(ttl=0)
        cache.set("k", "v")
        assert cache.get("k") is None

    def test_clear(self):
        cache = _TTLCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.size == 0

    def test_max_entries_eviction(self):
        cache = _TTLCache(ttl=60, max_entries=3)
        for i in range(5):
            cache.set(f"k{i}", i)
        assert cache.size <= 3

    def test_none_key(self):
        cache = _TTLCache()
        cache.set(None, "val")
        assert cache.get(None) == "val"


class TestSimulator:
    def test_density_map_all_zones(self):
        dm = get_zone_density_map(datetime(2026, 4, 19, 18, 0))
        assert set(dm.keys()) == set(ZONE_REGISTRY.keys())

    def test_density_bounds(self):
        dm = get_zone_density_map(datetime(2026, 4, 19, 12, 0))
        for density in dm.values():
            assert 0 <= density <= 100

    def test_peak_hour_detection(self):
        assert _is_peak_hour(18) is True
        assert _is_peak_hour(3) is False
        assert _is_peak_hour(13) is True
        assert _is_peak_hour(15) is False

    def test_density_to_status_critical(self):
        assert _density_to_status(90) == "CRITICAL"

    def test_density_to_status_high(self):
        assert _density_to_status(70) == "HIGH"

    def test_density_to_status_medium(self):
        assert _density_to_status(45) == "MEDIUM"

    def test_density_to_status_low(self):
        assert _density_to_status(10) == "LOW"

    def test_zone_crowd_detail_structure(self):
        dm = get_zone_density_map(datetime(2026, 4, 19, 14, 0))
        detail = get_zone_crowd_detail("GA", dm)
        assert "zone_id" in detail
        assert "name" in detail
        assert "density" in detail
        assert "status" in detail

    def test_zone_crowd_detail_unknown_zone(self):
        dm = get_zone_density_map()
        try:
            get_zone_crowd_detail("UNKNOWN", dm)
            assert False, "Should have raised KeyError"
        except KeyError:
            pass

    def test_event_phase_halftime_boosts_amenity(self):
        dm_live = get_zone_density_map(datetime(2026, 4, 19, 19, 0), event_phase="live")
        dm_half = get_zone_density_map(datetime(2026, 4, 19, 19, 0), event_phase="halftime")
        assert dm_half["FC"] >= dm_live["FC"]

    def test_event_phase_exit_boosts_gates(self):
        dm_live = get_zone_density_map(datetime(2026, 4, 19, 23, 0), event_phase="live")
        dm_exit = get_zone_density_map(datetime(2026, 4, 19, 23, 0), event_phase="exit")
        assert dm_exit["GA"] >= dm_live["GA"]


class TestPredictor:
    def test_predict_returns_required_fields(self):
        result = predict_zone_density("GA", 50, datetime(2026, 4, 19, 16, 0))
        assert "zone_id" in result
        assert "predicted_density" in result
        assert "trend" in result

    def test_predicted_density_bounded(self):
        result = predict_zone_density("GA", 95, datetime(2026, 4, 19, 18, 0))
        assert 0 <= result["predicted_density"] <= 100

    def test_trend_labels(self):
        assert _net_trend(10) == "INCREASING"
        assert _net_trend(-10) == "DECREASING"
        assert _net_trend(0) == "STABLE"

    def test_predict_all_zones(self):
        preds = predict_all_zones(datetime(2026, 4, 19, 17, 0))
        for zone_id in ZONE_REGISTRY:
            assert zone_id in preds

    def test_predict_with_inflow(self):
        result = predict_zone_density("GA", 40, inflow_rate=20.0, outflow_rate=5.0)
        assert result["flow_delta"] == 15

    def test_time_delta_approaching_peak(self):
        delta = _compute_time_delta(datetime(2026, 4, 19, 16, 45))
        assert delta == +15 or delta == +3 or delta == -3


class TestWaitTimes:
    def test_gate_wait_time(self):
        wait = calculate_service_wait_time("GA", {"type": "gate"}, 80)
        assert wait > 0

    def test_zero_density_no_wait(self):
        wait = calculate_service_wait_time("GA", {"type": "gate"}, 10)
        assert wait == 0

    def test_amenity_wait_time(self):
        wait = calculate_service_wait_time("FC", {"type": "amenity"}, 60)
        assert wait > 0

    def test_corridor_no_wait(self):
        wait = calculate_service_wait_time("C1", {"type": "corridor"}, 80)
        assert wait == 0

    def test_wait_trend_increasing(self):
        trend = determine_wait_trend(50, {"predicted_density": 70})
        assert trend == "INCREASING"

    def test_wait_trend_decreasing(self):
        trend = determine_wait_trend(70, {"predicted_density": 50})
        assert trend == "DECREASING"

    def test_wait_trend_stable(self):
        trend = determine_wait_trend(50, {"predicted_density": 52})
        assert trend == "STABLE"

    def test_wait_status_low(self):
        assert get_wait_status(2) == "LOW"

    def test_wait_status_moderate(self):
        assert get_wait_status(10) == "MODERATE"

    def test_wait_status_high(self):
        assert get_wait_status(20) == "HIGH"
