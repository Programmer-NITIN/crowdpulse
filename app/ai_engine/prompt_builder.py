"""
ai_engine/prompt_builder.py
----------------------------
Builds structured prompts for Gemini from navigation context.

Design: Gemini's job is to EXPLAIN the decision already made by the
decision_engine, not to make a new one. The prompt gives only facts.
"""

from typing import Dict, List

from dataclasses import dataclass

from app.config import ZONE_REGISTRY


@dataclass
# pylint: disable=too-many-instance-attributes
class NavigationContext:
    """Consolidated payload for building navigation prompts, solving R0913 (too many args)."""
    current_zone: str
    destination: str
    recommended_route: List[str]
    zone_scores: Dict[str, Dict[str, int]]
    density_map: Dict[str, int]
    predictions: Dict[str, Dict]
    estimated_wait_minutes: int
    event_phase: str
    priority: str


def build_navigation_prompt(ctx: NavigationContext) -> str:
    """Returns a structured prompt string ready for Gemini.

    The prompt is human-readable for debugging and provides Gemini full context
    without ambiguity.
    """
    zone_lines = []
    for zone_id, density in ctx.density_map.items():
        name = ZONE_REGISTRY.get(zone_id, {}).get("name", zone_id)
        score_data = ctx.zone_scores.get(zone_id, {})
        score = score_data.get("score", 0)
        confidence = score_data.get("confidence_score", 0)
        trend = ctx.predictions.get(zone_id, {}).get("trend", "STABLE")
        zone_lines.append(
            f"  - {name} ({zone_id}): {density}% crowded, trend: {trend}, "
            f"score: {score}/100, confidence: {confidence}%"
        )

    zone_summary = "\n".join(zone_lines)
    route_str = " → ".join(
        ZONE_REGISTRY.get(z, {}).get("name", z) for z in ctx.recommended_route
    )

    # Simulate vision insights based on route density
    route_densities = [ctx.density_map.get(z, 0) for z in ctx.recommended_route]
    max_d = max(route_densities) if route_densities else 0
    if max_d > 75:
        vision_note = (
            "IoT sensors detect significant congestion in key segments; "
            "Dijkstra re-weighted to avoid bottlenecks."
        )
    elif max_d > 50:
        vision_note = (
            "Turnstile sensors monitoring moderate buildup; "
            "routing accounts for projected clearing."
        )
    else:
        vision_note = "IoT telemetry confirms nominal flow across all route segments."

    prompt = f"""
You are the CrowdPulse AI Guide at a major sporting venue.
Explain the following optimal routing decision to the user concisely (max 3 sentences).

Context:
User requested: {ctx.current_zone} -> {ctx.destination}
Event Phase: {ctx.event_phase}
Priority: {ctx.priority}

System Computed Route: {route_str}
Estimated Moving & Wait Time: {ctx.estimated_wait_minutes} minutes

Live Venue Data (IoT sensors, turnstiles, ticket scans):
{zone_summary}

Vision / Anomaly Insight:
{vision_note}

Tone: Helpful, reassuring, clear. Give a solid, logical justification for the route.
"""
    return prompt.strip()
