"""
api/routes_crowd.py
-------------------
Endpoints for live crowd density, predictions, and service wait times.

All data comes from the deterministic crowd engine — no AI dependency.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from app.config import ZONE_REGISTRY
from app.crowd_engine.simulator import get_zone_density_map, get_zone_crowd_detail
from app.crowd_engine.predictor import predict_zone_density, PredictContext, predict_all_zones
from app.crowd_engine.wait_times import (
    calculate_service_wait_time,
    determine_wait_trend,
    get_wait_status,
)
from app.models.crowd_models import (
    CrowdStatusResponse,
    CrowdPredictionResponse,
    WaitTimeResponse,
    ServiceWaitTime,
)

router = APIRouter()


@router.get(
    "/crowd/status",
    response_model=CrowdStatusResponse,
    summary="Live crowd density for all zones",
)
async def get_crowd_status():
    """Returns current density readings for every zone in the venue.

    Data refreshes every 2 seconds via the simulation engine.
    """
    now = datetime.now()
    density_map = get_zone_density_map(now)
    zones = [
        get_zone_crowd_detail(zone_id, density_map)
        for zone_id in ZONE_REGISTRY
    ]
    return CrowdStatusResponse(timestamp=now, zones=zones)


@router.get(
    "/crowd/predict",
    response_model=CrowdPredictionResponse,
    summary="30-minute density prediction for a zone",
)
async def get_crowd_prediction(
    zone_id: str = Query(..., max_length=32, description="Zone ID to predict"),
    inflow_rate: float = Query(0.0, ge=0, le=100),
    outflow_rate: float = Query(0.0, ge=0, le=100),
    event_phase: str = Query("live", description="Current event phase"),
):
    """Predicts where crowd density is heading for a specific zone.

    Combines time-of-day peak analysis, manual flow overrides, and event
    phase surges into a single predicted density value.
    """
    if zone_id not in ZONE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found.")

    density_map = get_zone_density_map()
    ctx = PredictContext(
        inflow_rate=inflow_rate,
        outflow_rate=outflow_rate,
        event_phase=event_phase,
    )
    result = predict_zone_density(
        zone_id,
        density_map[zone_id],
        ctx
    )
    return CrowdPredictionResponse(**result)


@router.get(
    "/crowd/wait-times",
    response_model=WaitTimeResponse,
    summary="Service availability and estimated wait times",
)
async def get_wait_times():
    """Returns estimated wait times for all service zones (gates, food, restrooms, etc.)."""
    now = datetime.now()
    density_map = get_zone_density_map(now)
    predictions = predict_all_zones(now, density_map=density_map)

    services = []
    service_types = {"gate", "amenity", "restroom", "medical"}
    for zone_id, zone_data in ZONE_REGISTRY.items():
        if zone_data.get("type") not in service_types:
            continue
        density = density_map[zone_id]
        wait = calculate_service_wait_time(zone_id, zone_data, density)
        trend = determine_wait_trend(density, predictions.get(zone_id, {}))
        status = get_wait_status(wait)
        services.append(
            ServiceWaitTime(
                zone_id=zone_id,
                name=zone_data["name"],
                wait_minutes=wait,
                trend=trend,
                status=status,
            )
        )

    return WaitTimeResponse(timestamp=now, services=services)
