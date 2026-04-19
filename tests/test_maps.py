"""
tests/test_maps.py
------------------
Tests for the Google Maps client with mock fallback.
"""

from app.google_services.maps_client import (
    get_walking_distance,
    get_route_total_distance,
    get_zone_coordinates,
    get_route_waypoints,
    is_using_mock,
)
from app.config import ZONE_REGISTRY


class TestMapsClient:
    def test_is_using_mock(self):
        assert is_using_mock() is True

    def test_walking_distance_neighbors(self):
        dist = get_walking_distance("GA", "C1")
        assert dist == 55  # From ZONE_REGISTRY

    def test_walking_distance_non_neighbors(self):
        dist = get_walking_distance("GA", "ST")
        assert dist == 50  # Default fallback

    def test_route_total_distance(self):
        route = ["GA", "C1", "FC"]
        total = get_route_total_distance(route)
        assert total > 0
        assert total == 55 + 30  # GA→C1=55, C1→FC=30

    def test_route_total_distance_single_zone(self):
        assert get_route_total_distance(["GA"]) == 0

    def test_zone_coordinates_known(self):
        coords = get_zone_coordinates("GA")
        assert "lat" in coords
        assert "lng" in coords
        assert coords["lat"] > 0

    def test_zone_coordinates_unknown(self):
        coords = get_zone_coordinates("UNKNOWN")
        assert coords["lat"] == 0.0
        assert coords["lng"] == 0.0

    def test_route_waypoints(self):
        wps = get_route_waypoints(["GA", "C1", "FC"])
        assert len(wps) == 3
        assert wps[0]["zone_id"] == "GA"
        assert "lat" in wps[0]
        assert "lng" in wps[0]

    def test_route_waypoints_empty(self):
        wps = get_route_waypoints([])
        assert len(wps) == 0

    def test_all_zones_have_coordinates(self):
        for zone_id in ZONE_REGISTRY:
            coords = get_zone_coordinates(zone_id)
            assert coords["lat"] != 0.0 or coords["lng"] != 0.0, f"Zone {zone_id} missing coords"
