"""
models/analytics_models.py
--------------------------
Pydantic schemas for the analytics and staff operations dashboard.

These models validate the structure returned by the analytics endpoint
and ensure consistent data contracts between backend and frontend.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class LiveZoneStatus(BaseModel):
    """Live density reading for the staff leaderboard."""

    zone_id: str = Field(..., description="Unique zone identifier")
    name: str = Field(..., description="Human-readable zone name")
    current_density: int = Field(
        ..., ge=0, le=100, description="Current crowd density percentage"
    )
    status: str = Field(
        ...,
        description="Severity level: LOW, MEDIUM, HIGH, or CRITICAL",
    )


class AnalyticsResponse(BaseModel):
    """Aggregated analytics response for the staff dashboard."""

    historical_hotspots: list[str] = Field(
        ..., description="Names of historically most congested zones"
    )
    live_leaderboard: list[LiveZoneStatus] = Field(
        ..., description="All zones sorted by current density descending"
    )
    recommended_entry: str = Field(
        ..., description="Gate with the lowest current density"
    )
    ai_recommendations: list[str] = Field(
        default_factory=list,
        description="AI-generated crowd management recommendations",
    )
    operational_briefing: str = Field(
        default="",
        description="AI-generated operational summary for staff",
    )
    timestamp: datetime | None = Field(
        default=None, description="Response generation timestamp"
    )
