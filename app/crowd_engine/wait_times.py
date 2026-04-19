"""
crowd_engine/wait_times.py
--------------------------
Calculates estimated wait times for venue services based on live density.

Wait models:
  - Gates: quadratic growth (security queues explode at high density)
  - Restrooms: linear growth (max ~15 min)
  - Amenities: linear growth (max ~25 min)
  - Medical: linear growth (max ~20 min)
  - Others: no queue
"""

from typing import Dict, Any


def calculate_service_wait_time(
    _zone_id: str, zone_data: Dict[str, Any], density: int
) -> int:
    """Computes estimated wait time in minutes for a zone based on type and density."""
    if density < 20:
        return 0

    zone_type = zone_data.get("type", "corridor")
    density_factor = density / 100.0

    if zone_type == "gate":
        return int(30 * (density_factor ** 2))
    elif zone_type == "restroom":
        return int(15 * density_factor)
    elif zone_type == "amenity":
        return int(25 * density_factor)
    elif zone_type == "medical":
        return int(20 * density_factor)
    return 0


def determine_wait_trend(density: int, prediction: Dict[str, Any]) -> str:
    """Returns the wait time direction based on predicted density."""
    pred_density = prediction.get("predicted_density", density)
    if pred_density > density + 5:
        return "INCREASING"
    elif pred_density < density - 5:
        return "DECREASING"
    return "STABLE"


def get_wait_status(wait_minutes: int) -> str:
    """Classifies wait time into a category."""
    if wait_minutes < 5:
        return "LOW"
    elif wait_minutes < 15:
        return "MODERATE"
    return "HIGH"
