"""
ai_engine/staff_advisor.py
---------------------------
Gemini-powered AI advisor for venue operations staff.

Three capabilities:
1. generate_recommendations — crowd management strategies from live data.
2. triage_alert — assess an overcrowding alert and suggest response actions.
3. generate_briefing — pre-match operational summary.

Design: All functions fail gracefully to human-readable fallbacks.
"""

import logging
from typing import Any, Dict, List

import google.generativeai as genai

from app.config import settings, ZONE_REGISTRY

logger = logging.getLogger(__name__)

# ── Gemini singleton ─────────────────────────────────────────────────────────
_model: Any = None

if settings.gemini_api_key:
    try:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(settings.gemini_model)
    except Exception as exc:
        logger.error("StaffAdvisor: Gemini init failed: %s", exc)

_STAFF_CONTEXT = """You are CrowdPulse AI Operations Advisor for a large cricket stadium.
Analyze the provided real-time zone data and generate actionable crowd management recommendations.
Focus on:
1. Identifying zones approaching or at critical capacity
2. Suggesting crowd redirection strategies
3. Recommending staff deployment based on wait times and congestion
4. Flagging potential safety concerns based on patterns
Be specific — reference zone names, exact density percentages, and wait times.
Format as a numbered list of clear, actionable recommendations."""


def _format_zone_summary(density_map: Dict[str, int]) -> str:
    """Formats zone data as context for Gemini."""
    lines = []
    for zone_id, density in density_map.items():
        name = ZONE_REGISTRY.get(zone_id, {}).get("name", zone_id)
        ztype = ZONE_REGISTRY.get(zone_id, {}).get("type", "unknown")
        lines.append(f"- {name} ({ztype}): {density}% crowded")
    return "\n".join(lines)


def generate_recommendations(density_map: Dict[str, int]) -> List[str]:
    """Generates 3–5 crowd management recommendations from live zone data.

    Returns a list of recommendation strings. Falls back to a generic
    recommendation if Gemini is unavailable.
    """
    if not _model:
        return _fallback_recommendations(density_map)

    zone_summary = _format_zone_summary(density_map)
    prompt = f"""{_STAFF_CONTEXT}

CURRENT LIVE ZONE DATA:
{zone_summary}

Generate 3–5 specific, actionable crowd management recommendations:"""

    try:
        response = _model.generate_content(
            prompt,
            request_options={"timeout": settings.gemini_timeout_seconds},
        )
        text = response.text.strip()
        recommendations = [r.strip() for r in text.split("\n") if r.strip() and r.strip()[0].isdigit()]
        return recommendations if recommendations else [text]
    except Exception as exc:
        logger.error("StaffAdvisor: recommendations failed: %s", exc)
        return _fallback_recommendations(density_map)


def triage_alert(zone_id: str, density: int, density_map: Dict[str, int]) -> str:
    """Assesses an overcrowding alert and suggests response actions."""
    zone_name = ZONE_REGISTRY.get(zone_id, {}).get("name", zone_id)

    if not _model:
        return (
            f"ALERT: {zone_name} is at {density}% capacity. "
            f"Recommend deploying additional staff and activating crowd diversion protocols."
        )

    zone_summary = _format_zone_summary(density_map)
    prompt = f"""{_STAFF_CONTEXT}

OVERCROWDING ALERT:
- Zone: {zone_name} ({zone_id})
- Current Density: {density}%
- Severity: {"CRITICAL" if density >= 80 else "HIGH"}

ALL ZONE DATA:
{zone_summary}

Assess this alert and suggest 2–3 immediate response actions:"""

    try:
        response = _model.generate_content(
            prompt,
            request_options={"timeout": settings.gemini_timeout_seconds},
        )
        return response.text.strip()
    except Exception as exc:
        logger.error("StaffAdvisor: triage failed: %s", exc)
        return (
            f"Automatic triage failed. Manual assessment required for {zone_name} "
            f"at {density}% capacity."
        )


def generate_briefing(density_map: Dict[str, int]) -> str:
    """Generates a pre-match operational summary for staff."""
    if not _model:
        return _fallback_briefing(density_map)

    zone_summary = _format_zone_summary(density_map)
    prompt = f"""You are CrowdPulse AI Operations Advisor. Generate a concise pre-match
operational briefing (5–7 sentences) based on the current venue state.
Include: overall readiness, zones to watch, recommended gate prioritization,
and staff deployment suggestions.

CURRENT ZONE DATA:
{zone_summary}"""

    try:
        response = _model.generate_content(
            prompt,
            request_options={"timeout": settings.gemini_timeout_seconds},
        )
        return response.text.strip()
    except Exception as exc:
        logger.error("StaffAdvisor: briefing failed: %s", exc)
        return _fallback_briefing(density_map)


def _fallback_recommendations(density_map: Dict[str, int]) -> List[str]:
    """Deterministic recommendations when Gemini is unavailable."""
    recommendations = []
    for zone_id, density in density_map.items():
        name = ZONE_REGISTRY.get(zone_id, {}).get("name", zone_id)
        if density >= 80:
            recommendations.append(
                f"CRITICAL: {name} at {density}% — activate crowd diversion immediately."
            )
        elif density >= 60:
            recommendations.append(
                f"WARNING: {name} at {density}% — deploy additional staff for flow management."
            )
    if not recommendations:
        recommendations.append("All zones are operating within normal parameters.")
    return recommendations


def _fallback_briefing(density_map: Dict[str, int]) -> str:
    """Deterministic briefing when Gemini is unavailable."""
    critical = [z for z, d in density_map.items() if d >= 80]
    high = [z for z, d in density_map.items() if 60 <= d < 80]

    if critical:
        return f"ALERT: {len(critical)} zones at critical capacity. Immediate intervention required."
    if high:
        return f"NOTE: {len(high)} zones at high capacity. Monitor closely and prepare diversion plans."
    return "All zones within normal operating range. Standard staffing levels are sufficient."
