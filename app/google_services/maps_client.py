"""
google_services/maps_client.py
-------------------------------
Google Maps Platform client for walking distance and coordinates.

Design:
- In production: calls the Distance Matrix API for real walking distances.
- In development: returns pre-configured distances from the zone registry.
- Coordinates are always available from the zone registry.
"""

import logging
from typing import Any, Dict, List

from app.config import settings, ZONE_REGISTRY

logger = logging.getLogger(__name__)

# ── Client initialization ───────────────────────────────────────────────────
_client: Any = None
_using_mock = True

if settings.maps_enabled and settings.maps_api_key:
    try:
        import googlemaps
        _client = googlemaps.Client(key=settings.maps_api_key)
        _using_mock = False
        logger.info("Maps: Connected with API key.")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Maps: Connection failed — using mock. Error: %s", exc)
else:
    logger.info("Maps: Running in mock mode (MAPS_ENABLED=false).")


def get_walking_distance(origin_zone: str, dest_zone: str) -> int:
    """Returns walking distance in metres between two zones.

    Uses Google Distance Matrix API in production; falls back to
    pre-configured distances from ZONE_REGISTRY.
    """
    if _using_mock:
        return _mock_distance(origin_zone, dest_zone)

    try:
        origin_coords = ZONE_REGISTRY.get(origin_zone, {}).get("coordinates", {})
        dest_coords = ZONE_REGISTRY.get(dest_zone, {}).get("coordinates", {})

        if not origin_coords or not dest_coords:
            return _mock_distance(origin_zone, dest_zone)

        result = _client.distance_matrix(
            origins=[f"{origin_coords['lat']},{origin_coords['lng']}"],
            destinations=[f"{dest_coords['lat']},{dest_coords['lng']}"],
            mode="walking",
        )
        distance = result["rows"][0]["elements"][0]["distance"]["value"]
        return distance
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Maps: Distance request failed — using mock. %s", exc)
        return _mock_distance(origin_zone, dest_zone)


def get_route_total_distance(route: List[str]) -> int:
    """Returns total walking distance in metres for a multi-zone route."""
    total = 0
    for i in range(len(route) - 1):
        total += get_walking_distance(route[i], route[i + 1])
    return total


def get_zone_coordinates(zone_id: str) -> Dict[str, float]:
    """Returns lat/lng coordinates for a zone from the registry."""
    return ZONE_REGISTRY.get(zone_id, {}).get("coordinates", {"lat": 0.0, "lng": 0.0})


def get_route_waypoints(route: List[str]) -> List[Dict]:
    """Returns waypoints (zone_id + lat/lng) for all zones in a route."""
    return [
        {"zone_id": z, **get_zone_coordinates(z)}
        for z in route
    ]


def _mock_distance(origin: str, dest: str) -> int:
    """Returns pre-configured distance from the zone graph, or 50m default."""
    neighbors = ZONE_REGISTRY.get(origin, {}).get("neighbors", {})
    return neighbors.get(dest, 50)


def is_using_mock() -> bool:
    """Returns True if running in mock mode."""
    return _using_mock
