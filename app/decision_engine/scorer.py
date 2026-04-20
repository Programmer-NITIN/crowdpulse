"""
decision_engine/scorer.py
--------------------------
Scores each zone on a 0–100 scale (higher = better to visit).

Score formula:
  base_score = 100 − current_density
  trend_bonus = +10 if DECREASING, −10 if INCREASING, else 0
  capacity_factor: larger venues handle crowds better
  phase_penalty: penalize areas expected to be packed in current phase
  final = clamp(base + trend + capacity + phase, 0, 100)
"""

from typing import Dict

from typing_extensions import TypedDict

from app.config import ZONE_REGISTRY


class ZoneScore(TypedDict):
    """Structured return type for a single zone's score breakdown."""

    score: int
    confidence_score: int


def _calculate_trend_adjustment(trend: str) -> int:
    """Modifier based on predicted crowd trend direction."""
    return {"DECREASING": +10, "STABLE": 0, "INCREASING": -10}.get(trend, 0)


def _calculate_capacity_adjustment(zone_id: str) -> int:
    """Larger venues handle crowds better — slight score bonus."""
    capacity = ZONE_REGISTRY.get(zone_id, {}).get("capacity", 300)
    return min(10, (capacity - 200) // 50)


def _calculate_phase_adjustment(zone_id: str, event_phase: str) -> int:
    """Penalize routing to zones expected to be packed for specific phases."""
    ztype = ZONE_REGISTRY.get(zone_id, {}).get("type", "unknown")
    if event_phase == "halftime" and ztype in ("amenity", "restroom"):
        return -10
    if event_phase == "exit" and ztype == "gate":
        return -10
    if event_phase == "entry" and ztype == "gate":
        return -5
    return 0


def _calculate_confidence(score: int, trend: str) -> int:
    """Adjusts AI confidence based on directionality of the crowd."""
    if trend == "INCREASING":
        conf_raw = score - 5
    elif trend == "DECREASING":
        conf_raw = score + 5
    else:
        conf_raw = score
    return max(0, min(100, conf_raw))


def score_zone(
    zone_id: str,
    current_density: int,
    trend: str,
    event_phase: str = "live",
) -> ZoneScore:
    """Returns a ZoneScore with score and confidence_score (both 0–100)."""
    base_score = 100 - current_density
    raw = (
        base_score
        + _calculate_trend_adjustment(trend)
        + _calculate_capacity_adjustment(zone_id)
        + _calculate_phase_adjustment(zone_id, event_phase)
    )
    score = max(0, min(100, raw))
    return {"score": score, "confidence_score": _calculate_confidence(score, trend)}


def score_all_zones(
    density_map: Dict[str, int],
    predictions: Dict[str, Dict],
    event_phase: str = "live",
) -> Dict[str, ZoneScore]:
    """Returns {zone_id: ZoneScore} for all zones."""
    return {
        zone_id: score_zone(
            zone_id,
            density_map[zone_id],
            predictions[zone_id]["trend"],
            event_phase,
        )
        for zone_id in density_map
    }
