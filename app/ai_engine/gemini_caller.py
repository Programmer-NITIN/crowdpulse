"""
ai_engine/gemini_caller.py
----------------------------
Shared utility for calling Gemini with timeout and graceful fallback.

Eliminates code duplication across explainer and staff_advisor modules.
"""

import logging
from typing import Any, Callable, TypeVar

from app.config import settings

logger = logging.getLogger(__name__)
T = TypeVar("T")


def call_gemini(
    model: Any,
    prompt: Any,
    fallback_fn: Callable[[], T],
    caller_name: str = "Gemini",
) -> T:
    """Calls Gemini with configured timeout; returns fallback on failure.

    Args:
        model: The GenerativeModel instance (or None).
        prompt: Prompt string or contents list for generate_content().
        fallback_fn: Zero-arg callable returning the fallback value.
        caller_name: Label for error logs.

    Returns:
        The model's text response (stripped) or the fallback value.
    """
    if model is None:
        return fallback_fn()
    try:
        response = model.generate_content(
            prompt,
            request_options={"timeout": settings.gemini_timeout_seconds},
        )
        return response.text.strip()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("%s: call failed: %s", caller_name, exc)
        return fallback_fn()
