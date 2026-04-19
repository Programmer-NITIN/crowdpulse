"""
ai_engine/chatbot.py
--------------------
Event Assistant chatbot for the CrowdPulse venue platform.

Design constraints:
- Intent classification is deterministic — no AI involved in deciding intent.
- Facts are resolved from config_data.py BEFORE Gemini is ever called.
- Gemini phrases grounded responses; it never invents venue facts.
- Route/wait questions are redirected to the deterministic route planner.
- Falls back safely when Gemini is unavailable.
"""

import logging
from typing import Optional, Any

import google.generativeai as genai

from app.config import settings
from app.config_data import EVENT_INFO, VENUE_POLICY

logger = logging.getLogger(__name__)

# ── Gemini initialisation ────────────────────────────────────────────────────
_model: Any = None
try:
    if settings.gemini_api_key:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(settings.gemini_model)
    else:
        logger.warning("Chatbot: Gemini not configured — structured-data-only mode.")
except Exception as exc:  # pylint: disable=broad-exception-caught
    logger.error("Chatbot: Failed to initialise Gemini: %s", exc)


# ── System instruction ───────────────────────────────────────────────────────
_SYSTEM_INSTRUCTION = f"""
You are the Official Event Assistant for the {EVENT_INFO['event_name']} at {EVENT_INFO['venue']}.

### CRITICAL RULES
1. You may ONLY use the grounded fact context provided in each message.
   Never invent venue policies, item rules, or timings.
2. If asked about routes, wait times, or crowd levels, respond EXACTLY:
   "Please use the Route Planner on this page for live route and wait information."
3. If factual context is missing, say:
   "I don't have that information — please ask a steward or visit the Information Desk near Gate A."
4. Keep answers short, plain, and scannable (prefer bullet points for lists).
5. Never speculate about safety, medical, or emergency guidance beyond what's provided.

You will receive grounded context prepended to each question.
"""


# ── Intent keyword sets ──────────────────────────────────────────────────────
_ROUTE_KEYWORDS = (
    "route", "path", "way to", "how to get", "get to", "go to", "find the",
    "fastest", "navigate", "directions",
    "wait", "queue", "line", "how long", "restroom wait", "bathroom",
    "which gate", "crowd level", "crowded",
)
_PROHIBITED_KEYWORDS = (
    "not allowed", "prohibited", "banned", "can i bring", "forbidden",
    "allowed in", "items", "what can", "bring into",
)
_BAG_KEYWORDS = ("bag", "backpack", "clear bag", "bag policy", "purse", "luggage")
_ACCESSIBILITY_KEYWORDS = (
    "wheelchair", "disabled", "accessible", "accessibility", "hearing loop",
    "sign language", "mobility", "assistance dog", "quiet area", "ambulant", "sensory",
)
_RE_ENTRY_KEYWORDS = (
    "re-entry", "re entry", "reentry", "leave and come back",
    "exit and return", "come back in", "go back in",
)
_RESTRICTED_KEYWORDS = (
    "restricted", "vip", "hospitality", "media", "staff only",
    "press", "pitch side", "pavilion", "members",
)
_TIMING_KEYWORDS = (
    "when does", "what time", "kick off", "start time", "gates open",
    "halftime", "innings break", "end time", "schedule", "programme",
)
_TICKET_KEYWORDS = ("ticket", "qr code", "season", "digital ticket", "paper ticket")
_FIRST_AID_KEYWORDS = (
    "first aid", "medical", "defibrillator", "emergency", "injured", "ambulance",
)
_LOST_PROPERTY_KEYWORDS = ("lost", "found", "lost property", "missing", "left behind")
_PARKING_KEYWORDS = ("parking", "park", "car", "auto", "rickshaw", "taxi", "uber", "ola")
_WEATHER_KEYWORDS = ("rain", "weather", "delay", "cancelled", "refund")


def _classify_intent(query_input: str) -> Optional[str]:
    """Returns an intent label or None if no grounded intent matches.

    Always lowercases the input for case-insensitive matching.
    """
    query_lower = query_input.lower()
    intent_map = [
        (_ROUTE_KEYWORDS, "route"),
        (_PROHIBITED_KEYWORDS, "prohibited"),
        (_BAG_KEYWORDS, "bag"),
        (_ACCESSIBILITY_KEYWORDS, "accessibility"),
        (_RE_ENTRY_KEYWORDS, "reentry"),
        (_RESTRICTED_KEYWORDS, "restricted"),
        (_TIMING_KEYWORDS, "timing"),
        (_TICKET_KEYWORDS, "ticket"),
        (_FIRST_AID_KEYWORDS, "first_aid"),
        (_LOST_PROPERTY_KEYWORDS, "lost_property"),
        (_PARKING_KEYWORDS, "parking"),
        (_WEATHER_KEYWORDS, "weather"),
    ]
    for keywords, intent in intent_map:
        if any(k in query_lower for k in keywords):
            return intent
    return None


def _build_grounded_context(intent: str) -> str:
    """Maps an intent to structured-data excerpt for Gemini grounding."""
    context_map = {
        "prohibited": (
            "Prohibited items:\n"
            + "\n".join(f"- {i}" for i in VENUE_POLICY["prohibited_items"])
        ),
        "bag": f"Bag policy: {VENUE_POLICY['bag_policy']}",
        "accessibility": "Accessibility services:\n" + "\n".join(f"- {s}" for s in VENUE_POLICY["accessibility_services"]),
        "reentry": f"Re-entry rules: {VENUE_POLICY['re_entry_rules']}",
        "restricted": f"Restricted areas: {VENUE_POLICY['restricted_areas']}",
        "timing": (
            f"Event: {EVENT_INFO['event_name']}\n"
            f"Date: {EVENT_INFO['date']}\n"
            f"Match start: {EVENT_INFO['match_start_time']}\n"
            f"Schedule:\n" + "\n".join(f"- {p}" for p in EVENT_INFO["key_phases"])
        ),
        "ticket": f"Ticket guidance: {VENUE_POLICY['ticket_guidance']}",
        "first_aid": f"First-aid information: {VENUE_POLICY['first_aid']}",
        "lost_property": f"Lost property: {VENUE_POLICY['lost_property']}",
        "parking": f"Parking and transport: {VENUE_POLICY['parking']}",
        "weather": f"Weather policy: {VENUE_POLICY['weather_policy']}",
    }
    return context_map.get(intent, "")


def _direct_response(intent: str) -> str:
    """Plain-text response from structured data when Gemini is unavailable."""
    ctx = _build_grounded_context(intent)
    if ctx:
        return ctx
    return "I don't have that information — please ask a steward or visit the Information Desk near Gate A."


def get_chat_response(query: str, history: Optional[list] = None) -> tuple[str, Optional[str], bool]:
    """Returns (reply, intent, grounded) for the attendee's question.

    Flow:
    1. Classify intent deterministically.
    2. Route/wait → redirect immediately (no AI).
    3. Grounded intent → Gemini phrases it naturally (or fallback).
    4. Unknown intent → safety fallback.
    """
    query_lower = query.lower()
    intent = _classify_intent(query_lower)

    # Route handoff
    if intent == "route":
        return (
            "Please use the Route Planner on this page for live route recommendations "
            "and wait-time estimates — it uses real-time crowd data to find the best path.",
            "route",
            True,
        )

    # Grounded intent
    if intent:
        context = _build_grounded_context(intent)
        if not _model:
            return (_direct_response(intent), intent, True)

        try:
            grounded_prompt = (
                f"{_SYSTEM_INSTRUCTION}\n\n"
                f"### Grounded Context\n{context}\n\n"
                f"### Attendee Question\n{query}"
            )
            history_turns: list[Any] = []
            for msg in (history or [])[-4:]:
                role = "user" if msg.get("role") == "user" else "model"
                history_turns.append({"role": role, "parts": [msg.get("content", "")]})

            contents: list[Any] = [{"role": "user", "parts": [grounded_prompt]}]
            contents.extend(history_turns)
            if history_turns:
                contents.append({"role": "user", "parts": [query]})

            response = _model.generate_content(
                contents,
                request_options={"timeout": settings.gemini_timeout_seconds},
            )
            return (response.text.strip(), intent, True)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Chatbot: Gemini phrasing failed: %s", exc)
            return (_direct_response(intent), intent, True)

    # Unknown intent
    if not _model:
        return (
            "I'm currently offline. For venue help, visit the Information Desk near Gate A.",
            None,
            False,
        )

    try:
        unknown_prompt = (
            f"{_SYSTEM_INSTRUCTION}\n\n"
            f"### Attendee Question\n{query}\n\n"
            f"Note: No specific grounded context is available. Respond using rule 3 only."
        )
        response = _model.generate_content(
            [{"role": "user", "parts": [unknown_prompt]}],
            request_options={"timeout": settings.gemini_timeout_seconds},
        )
        return (response.text.strip(), None, False)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Chatbot: Gemini fallback failed: %s", exc)
        return (
            "I'm experiencing technical difficulties. Please ask a steward or visit "
            "the Information Desk near Gate A.",
            None,
            False,
        )
