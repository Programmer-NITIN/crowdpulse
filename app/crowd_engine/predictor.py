"""
crowd_engine/predictor.py
--------------------------
Predicts crowd density 30 minutes into the future.

Two prediction signals are combined:
  1. Time-based: peak-window approach/leave → ±15/−12
  2. Flow-based: inflow_rate − outflow_rate
  3. Phase-based: event-phase-aware adjustments

Final: predicted = clamp(current + time_delta + flow_delta + phase_delta, 0, 100)
Trend is derived from the NET combined delta.
"""

from datetime import datetime, timedelta
from typing import Dict

from app.config import PEAK_HOUR_WINDOWS, ZONE_REGISTRY
from app.crowd_engine.simulator import get_zone_density_map

PREDICTION_WINDOW_MINUTES = 30
_TREND_THRESHOLD = 3


def _next_hour_is_peak(now: datetime) -> bool:
    """Check if the time 30 minutes from now falls within a peak window."""
    future = now + timedelta(minutes=PREDICTION_WINDOW_MINUTES)
    return any(start <= future.hour < end for start, end in PEAK_HOUR_WINDOWS)


def _current_hour_is_peak(now: datetime) -> bool:
    """Check if the current hour is within a peak window."""
    return any(start <= now.hour < end for start, end in PEAK_HOUR_WINDOWS)


def _compute_time_delta(now: datetime) -> int:
    """Returns the time-based crowd delta from peak-hour logic."""
    currently_peak = _current_hour_is_peak(now)
    next_is_peak = _next_hour_is_peak(now)

    if next_is_peak and not currently_peak:
        return +15  # Approaching a peak window — surge expected
    if currently_peak and not next_is_peak:
        return -12  # Leaving a peak window — dispersal expected
    return +3 if currently_peak else -3


def _compute_flow_delta(inflow_rate: float, outflow_rate: float) -> int:
    """Returns the flow-based crowd delta.

    Args:
        inflow_rate:  Percentage points of capacity arriving per 30 min.
        outflow_rate: Percentage points of capacity leaving per 30 min.
    """
    return round(inflow_rate - outflow_rate)


def _net_trend(net_delta: int) -> str:
    """Maps a net numeric delta to a human-readable trend label."""
    if net_delta > _TREND_THRESHOLD:
        return "INCREASING"
    if net_delta < -_TREND_THRESHOLD:
        return "DECREASING"
    return "STABLE"


def _compute_phase_delta(zone_id: str, event_phase: str) -> int:
    """Adjusts prediction based on event phase context."""
    ztype = ZONE_REGISTRY.get(zone_id, {}).get("type", "unknown")
    if event_phase == "halftime" and ztype in ("amenity", "restroom"):
        return 15
    if event_phase == "exit" and ztype == "gate":
        return 20
    if event_phase == "entry" and ztype == "gate":
        return 10
    return 0


def predict_zone_density(
    zone_id: str,
    current_density: int,
    now: datetime | None = None,
    inflow_rate: float = 0.0,
    outflow_rate: float = 0.0,
    event_phase: str = "live",
) -> Dict:
    """Predicts crowd density for a zone 30 minutes from now.

    Combines time-based (peak-hour) and flow-based signals additively.
    Returns a dict with zone_id, predicted_density, trend, and diagnostics.
    """
    now = now or datetime.now()

    time_delta = _compute_time_delta(now)
    flow_delta = _compute_flow_delta(inflow_rate, outflow_rate)
    phase_delta = _compute_phase_delta(zone_id, event_phase)

    net_delta = time_delta + flow_delta + phase_delta
    predicted = max(0, min(100, current_density + net_delta))
    trend = _net_trend(net_delta)

    return {
        "zone_id": zone_id,
        "current_density": current_density,
        "predicted_density": predicted,
        "trend": trend,
        "prediction_window_minutes": PREDICTION_WINDOW_MINUTES,
        "inflow_rate": inflow_rate,
        "outflow_rate": outflow_rate,
        "flow_delta": flow_delta,
    }


def predict_all_zones(
    now: datetime | None = None,
    flow_rates: Dict[str, Dict[str, float]] | None = None,
    event_phase: str = "live",
    density_map: Dict[str, int] | None = None,
) -> Dict[str, Dict]:
    """Returns predictions for every zone as {zone_id: prediction_dict}.

    Args:
        now:         Reference time. Defaults to datetime.now().
        flow_rates:  Optional per-zone flow overrides.
        event_phase: Current event phase label.
        density_map: Pre-computed density map to avoid redundant simulation.
    """
    now = now or datetime.now()
    flow_rates = flow_rates or {}
    if density_map is None:
        density_map = get_zone_density_map(now)

    return {
        zone_id: predict_zone_density(
            zone_id,
            density,
            now,
            inflow_rate=flow_rates.get(zone_id, {}).get("inflow_rate", 0.0),
            outflow_rate=flow_rates.get(zone_id, {}).get("outflow_rate", 0.0),
            event_phase=event_phase,
        )
        for zone_id, density in density_map.items()
    }
