"""
api/routes_navigation.py
-------------------------
Core navigation endpoint orchestrating all engines:
  1. Crowd engine → live density + predictions
  2. Decision engine → scoring + Dijkstra routing
  3. Maps client → walking distance + waypoints
  4. AI engine → Gemini explanation
  5. Firestore → session persistence

The route planner is fully deterministic. AI is used only for explanation.
"""

import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from app.config import ZONE_REGISTRY
from app.crowd_engine.simulator import get_zone_density_map
from app.crowd_engine.predictor import predict_all_zones
from app.decision_engine.scorer import score_all_zones
from app.decision_engine.router import find_best_route, estimate_wait_minutes, RouteContext
from app.ai_engine.prompt_builder import build_navigation_prompt, NavigationContext
from app.ai_engine.explainer import get_ai_explanation
from app.google_services import firestore_client, maps_client
from app.google_services.cloud_logging import log_info
from app.middleware.rate_limiter import navigation_rate_limit
from app.models.navigation_models import (
    NavigationRequest,
    NavigationResponse,
    ReasoningSummary,
    Waypoint,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Name-to-ID mapping for friendly input
_NAME_TO_ID = {v["name"].lower(): k for k, v in ZONE_REGISTRY.items()}
_NAME_TO_ID.update({k.lower(): k for k in ZONE_REGISTRY})

# Cache for recent navigation results to detect reroute opportunities
_nav_cache: dict = {}


def _resolve_zone(zone_input: str) -> str | None:
    """Resolves a zone ID or name to the canonical zone ID."""
    if zone_input in ZONE_REGISTRY:
        return zone_input
    return _NAME_TO_ID.get(zone_input.lower())


@router.post(
    "/navigate/suggest",
    response_model=NavigationResponse,
    summary="Compute optimal route between two zones",
    dependencies=[Depends(navigation_rate_limit)],
)
# pylint: disable=too-many-locals
async def suggest_navigation(req: NavigationRequest):
    """Main navigation orchestrator.

    Pipeline:
    1. Resolve zone identifiers (support both IDs and names).
    2. Generate live crowd density for all zones.
    3. Predict crowd density 30 minutes ahead.
    4. Score each zone on a 0-100 scale.
    5. Run Dijkstra to find the best route.
    6. Calculate walking distance and waypoints via Maps.
    7. Build a structured prompt and call Gemini for explanation.
    8. Persist the session to Firestore.
    9. Return the complete NavigationResponse.
    """
    # 1. Resolve zones
    source = _resolve_zone(req.current_zone)
    destination = _resolve_zone(req.destination)

    if not source:
        raise HTTPException(
            status_code=404,
            detail=f"Source zone '{req.current_zone}' not found.",
        )
    if not destination:
        raise HTTPException(
            status_code=404,
            detail=f"Destination zone '{req.destination}' not found.",
        )

    # 2. Live density
    now = datetime.now()
    density_map = get_zone_density_map(now)

    # 3. Predictions
    predictions = predict_all_zones(now, density_map=density_map)

    # 4. Zone scoring
    zone_scores = score_all_zones(density_map, predictions, req.event_phase.value)

    route = find_best_route(
        source,
        destination,
        zone_scores,
        RouteContext(
            predictions=predictions,
            constraints=req.constraints,
            priority=req.priority
        )
    )

    if route is None:
        raise HTTPException(
            status_code=404,
            detail=f"No path found from '{source}' to '{destination}'.",
        )

    # 6. Distance and waypoints
    wait_minutes = estimate_wait_minutes(route, density_map)
    total_distance = maps_client.get_route_total_distance(route)
    waypoints = [
        Waypoint(**wp) for wp in maps_client.get_route_waypoints(route)
    ]

    # 7. Reasoning summary
    avg_d = sum(density_map.values()) / len(density_map) if density_map else 0
    reasoning = ReasoningSummary(
        density_factor=round(avg_d / 100, 2),
        trend_factor=round(
            sum(1 for p in predictions.values() if p.get("trend") == "INCREASING")
            / max(len(predictions), 1),
            2,
        ),
        event_factor=0.6 if req.event_phase.value in ("live", "halftime") else 0.3,
    )

    # 8. AI explanation
    prompt = build_navigation_prompt(
        NavigationContext(
            current_zone=source,
            destination=destination,
            recommended_route=route,
            zone_scores=zone_scores,
            density_map=density_map,
            predictions=predictions,
            estimated_wait_minutes=wait_minutes,
            event_phase=req.event_phase.value,
            priority=req.priority.value,
        )
    )
    ai_explanation = get_ai_explanation(prompt)

    # 9. Persist to Firestore
    session_id = str(uuid.uuid4())
    firestore_client.store_document(
        "navigation_sessions",
        session_id,
        {
            "user_id": req.user_id,
            "route": route,
            "timestamp": now.isoformat(),
            "source": source,
            "destination": destination,
        },
    )

    log_info("Navigation computed", {
        "user_id": req.user_id,
        "source": source,
        "destination": destination,
        "route_length": len(route),
    })

    return NavigationResponse(
        user_id=req.user_id,
        recommended_route=route,
        estimated_wait_minutes=wait_minutes,
        total_walking_distance_meters=total_distance,
        route_waypoints=waypoints,
        zone_scores=zone_scores,
        reasoning_summary=reasoning,
        ai_explanation=ai_explanation,
    )
