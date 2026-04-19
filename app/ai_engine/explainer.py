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
from typing import Any

import google.generativeai as genai

from app.config import settings
from app.ai_engine.gemini_caller import call_gemini

logger = logging.getLogger(__name__)

# ── Module-level singleton ───────────────────────────────────────────────────
_model: Any = None

if settings.gemini_api_key:
    try:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(settings.gemini_model)
        logger.info("Explainer: Gemini model '%s' ready.", settings.gemini_model)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Explainer: Failed to initialize Gemini: %s", exc)
else:
    logger.warning("Explainer: GEMINI_API_KEY not set — returning fallback explanations.")


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
