"""
api/routes_analytics.py
-----------------------
Staff operations dashboard and analytics endpoints.

Combines:
  - BigQuery historical hotspot data
  - Live density leaderboard
  - Staff AI recommendations
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from app.config import ZONE_REGISTRY
from app.crowd_engine.simulator import get_zone_density_map
from app.google_services import bigquery_client
from app.ai_engine.staff_advisor import generate_recommendations, generate_briefing
from app.middleware.rate_limiter import analytics_rate_limit
from app.models.analytics_models import AnalyticsResponse

router = APIRouter()


@router.get(
    "/analytics/dashboard",
    response_model=AnalyticsResponse,
    summary="Staff operations dashboard",
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_staff_dashboard():
    """Returns a comprehensive operations dashboard for venue staff.

    Includes historical hotspot data from BigQuery, live density leaderboard,
    recommended entry gate, and AI-powered crowd management recommendations.
    """
    now = datetime.now()
    density_map = get_zone_density_map(now)

    # BigQuery historical data
    hotspots = bigquery_client.get_historical_hotspots(top_n=5)

    # Live leaderboard sorted by density descending
    leaderboard = sorted(
        [
            {
                "zone_id": zid,
                "name": ZONE_REGISTRY[zid]["name"],
                "current_density": density,
                "status": "CRITICAL" if density >= 80 else "HIGH" if density >= 60 else "MEDIUM" if density >= 35 else "LOW",
            }
            for zid, density in density_map.items()
        ],
        key=lambda z: z["current_density"],
        reverse=True,
    )

    # Best entry gate
    gate_densities = {
        zid: density
        for zid, density in density_map.items()
        if ZONE_REGISTRY[zid].get("type") == "gate"
    }
    best_gate = min(gate_densities, key=gate_densities.get) if gate_densities else "GA"
    recommended_entry = ZONE_REGISTRY.get(best_gate, {}).get("name", best_gate)

    # AI recommendations
    recommendations = generate_recommendations(density_map)

    # Operational briefing
    briefing = generate_briefing(density_map)

    return {
        "historical_hotspots": hotspots,
        "live_leaderboard": leaderboard,
        "recommended_entry": recommended_entry,
        "ai_recommendations": recommendations,
        "operational_briefing": briefing,
        "timestamp": now.isoformat(),
    }
