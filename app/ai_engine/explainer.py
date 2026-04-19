"""
ai_engine/explainer.py
-----------------------
Calls Gemini to produce a human-readable explanation of the navigation decision.

Design rules:
  - Gemini is NEVER used for routing decisions — only for explanation.
  - Module-level singleton model to avoid re-initialization per request.
  - Falls back gracefully so Gemini outage never breaks navigation.
"""

import logging

from app.ai_engine.gemini_caller import call_gemini, create_gemini_model

logger = logging.getLogger(__name__)

# ── Module-level singleton ───────────────────────────────────────────────────
_model = create_gemini_model("Explainer")


def get_ai_explanation(prompt: str) -> str:
    """Sends prompt to Gemini; returns explanation or deterministic fallback.

    The fallback ensures navigation responses never fail due to an AI outage.
    """
    return call_gemini(_model, prompt, _fallback_explanation, "Explainer")


def _fallback_explanation() -> str:
    """Deterministic explanation when Gemini is unavailable."""
    return (
        "This route was selected because it passes through the least congested zones "
        "based on current crowd density readings and predicted trend analysis. Follow "
        "the suggested path for the quickest and most comfortable journey through the venue."
    )
