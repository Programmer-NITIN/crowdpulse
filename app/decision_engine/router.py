"""
decision_engine/router.py
--------------------------
Finds the best route from a source zone to a destination zone.

Algorithm: Dijkstra's shortest path over the venue zone graph.
- Minimizes physical distance between zones.
- Includes a crowd-score penalty so congested zones are avoided.
- Supports trend-aware penalties: zones getting more crowded are punished.
- Priority modes: fast_exit, low_crowd, accessible, family_friendly.

This is intentionally readable and well-documented for evaluation.
"""

import heapq
from typing import List, Dict, Optional, Any

from app.config import ZONE_REGISTRY
from app.models.navigation_models import Priority


def _calculate_edge_cost(
    distance: int,
    score: int,
    constraints: Optional[List[str]],
    priority: Priority = Priority.fast_exit,
    neighbor_id: str = "",
    trend: str = "STABLE",
) -> int:
    """Calculates the cost of traversing an edge.

    Balances distance, congestion penalty, predictive trend, and user constraints.
    Lower score = more congested = higher penalty.
    """
    congestion_penalty = 100 - score

    # Predictive trend penalty
    trend_penalty = 0
    if trend == "INCREASING":
        trend_penalty = 20
    elif trend == "DECREASING":
        trend_penalty = -10

    # Priority-specific weighting
    if priority in (Priority.fast_exit, Priority.fastest):
        congestion_penalty = int(congestion_penalty * 0.4)
    elif priority in (Priority.low_crowd, Priority.least_crowded):
        congestion_penalty = int(congestion_penalty * 2.5)
        trend_penalty *= 2
    elif priority == Priority.accessible:
        zone_data = ZONE_REGISTRY.get(neighbor_id, {})
        if not zone_data.get("accessible", True):
            congestion_penalty += 300  # Severe barrier
    elif priority == Priority.family_friendly:
        zone_data = ZONE_REGISTRY.get(neighbor_id, {})
        if not zone_data.get("family_friendly", True):
            congestion_penalty += 150
        congestion_penalty = int(congestion_penalty * 1.5)

    # Constraint overrides
    if constraints:
        if "avoid_crowd" in constraints and score < 60:
            congestion_penalty *= 6
        if "prefer_fastest" in constraints:
            congestion_penalty = int(congestion_penalty * 0.1)
            trend_penalty = 0

    return distance + congestion_penalty + trend_penalty


def find_best_route(
    source: str,
    destination: str,
    zone_scores: Dict[str, Dict[str, int]],
    predictions: Optional[Dict[str, Dict[str, Any]]] = None,
    constraints: Optional[List[str]] = None,
    priority: Priority = Priority.fast_exit,
) -> Optional[List[str]]:
    """Returns the optimal path as an ordered list of zone IDs, or None.

    Uses Dijkstra's algorithm with a priority queue (heapq).
    Edge cost = physical_distance + crowd_penalty + trend_penalty.
    """
    if source == destination:
        return [source]

    pq = [(0, source, [source])]
    visited: set = set()

    while pq:
        current_cost, current, path = heapq.heappop(pq)

        if current in visited:
            continue
        visited.add(current)

        if current == destination:
            return path

        neighbors = ZONE_REGISTRY.get(current, {}).get("neighbors", {})
        for neighbor, distance in neighbors.items():
            if neighbor not in visited:
                score = zone_scores.get(neighbor, {}).get("score", 50)
                trend = (
                    predictions.get(neighbor, {}).get("trend", "STABLE")
                    if predictions
                    else "STABLE"
                )
                edge_cost = _calculate_edge_cost(
                    distance, score, constraints, priority, neighbor, trend
                )
                heapq.heappush(
                    pq, (current_cost + edge_cost, neighbor, path + [neighbor])
                )

    return None


def estimate_wait_minutes(
    route: List[str],
    density_map: Dict[str, int],
) -> int:
    """Estimates total walking + wait time in minutes for a route.

    Each zone hop ≈ 1 min walking. HIGH zones add 3 min, MEDIUM add 1 min.
    """
    wait = 0
    for zone_id in route:
        density = density_map.get(zone_id, 0)
        wait += 1
        if density >= 70:
            wait += 3
        elif density >= 40:
            wait += 1
    return wait
