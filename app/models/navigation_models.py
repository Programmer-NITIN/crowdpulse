"""
models/navigation_models.py
----------------------------
Pydantic schemas for navigation request/response.

Security bounds:
- user_id:      max 64 chars.
- current_zone / destination: max 32 chars.
- user_note:    max 256 chars — free-text field; bounded to prevent log injection.
- constraints:  max 5 items — prevents constraint explosion in the router.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.crowd_models import EventPhase


class Priority(str, Enum):
    """Route optimization strategy selected by the user."""

    FAST_EXIT = "fast_exit"
    LOW_CROWD = "low_crowd"
    ACCESSIBLE = "accessible"
    FAMILY_FRIENDLY = "family_friendly"
    FASTEST = "fastest"
    LEAST_CROWDED = "least_crowded"


class NavigationRequest(BaseModel):
    """Inbound request for a route computation."""

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique user identifier",
    )
    current_zone: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Zone where the user currently is",
    )
    destination: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Destination zone ID or name",
    )
    priority: Priority = Priority.FAST_EXIT
    event_phase: EventPhase = EventPhase.LIVE
    constraints: Optional[List[str]] = Field(
        default_factory=lambda: [],
        max_length=5,
        description="Routing constraints like 'avoid_crowd'. Max 5.",
    )
    user_note: Optional[str] = Field(
        None,
        max_length=256,
        description="Optional text note from user. Max 256 chars.",
    )


class ZoneScoreDetail(BaseModel):
    """Scoring breakdown for a single zone."""

    score: int
    confidence_score: int


class ReasoningSummary(BaseModel):
    """AI reasoning factor weights used in route selection."""

    density_factor: float = Field(..., description="Weight of density signal (0–1)")
    trend_factor: float = Field(..., description="Weight of crowd trend signal (0–1)")
    event_factor: float = Field(..., description="Weight of event phase signal (0–1)")


class Waypoint(BaseModel):
    """GPS coordinate for a zone along the route."""

    zone_id: str
    lat: float
    lng: float


class NavigationResponse(BaseModel):
    """Full route recommendation returned to the client."""

    user_id: str
    recommended_route: List[str]
    estimated_wait_minutes: int
    total_walking_distance_meters: int = 0
    route_waypoints: List[Waypoint] = Field(default_factory=list)
    zone_scores: Dict[str, ZoneScoreDetail]
    reasoning_summary: ReasoningSummary
    ai_explanation: Optional[str] = None


class RerouteAlertResponse(BaseModel):
    """Live reroute alert when a significantly better path is detected."""

    requires_reroute: bool
    new_navigation: Optional[NavigationResponse] = None
