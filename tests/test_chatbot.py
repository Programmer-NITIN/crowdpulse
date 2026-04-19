"""
tests/test_chatbot.py
---------------------
Tests for the deterministic intent classification and grounded chatbot.
"""

from app.ai_engine.chatbot import _classify_intent, _build_grounded_context, get_chat_response


class TestIntentClassification:
    def test_prohibited_intent(self):
        assert _classify_intent("what items are not allowed") == "prohibited"

    def test_bag_intent(self):
        assert _classify_intent("what is the bag policy") == "bag"

    def test_route_intent(self):
        assert _classify_intent("how do i get to the food court") == "route"

    def test_accessibility_intent(self):
        assert _classify_intent("where is the wheelchair area") == "accessibility"

    def test_reentry_intent(self):
        assert _classify_intent("can i leave and come back") == "reentry"

    def test_timing_intent(self):
        assert _classify_intent("when does the match start") == "timing"

    def test_ticket_intent(self):
        assert _classify_intent("do i need a digital ticket") == "ticket"

    def test_first_aid_intent(self):
        assert _classify_intent("where is first aid") == "first_aid"

    def test_parking_intent(self):
        assert _classify_intent("where can i park my car") == "parking"

    def test_lost_property_intent(self):
        assert _classify_intent("i lost my wallet") == "lost_property"

    def test_weather_intent(self):
        assert _classify_intent("what if it rains") == "weather"

    def test_restricted_intent(self):
        assert _classify_intent("is the vip area open") == "restricted"

    def test_unknown_intent(self):
        assert _classify_intent("who is the best cricketer ever") is None

    def test_multiple_keywords_first_match(self):
        result = _classify_intent("how to get to the restricted area")
        assert result in ("route", "restricted")

    def test_case_insensitive(self):
        assert _classify_intent("WHAT ITEMS ARE PROHIBITED") == "prohibited"


class TestGroundedContext:
    def test_prohibited_context_has_items(self):
        ctx = _build_grounded_context("prohibited")
        assert "Weapons" in ctx or "weapons" in ctx.lower()

    def test_timing_context_has_schedule(self):
        ctx = _build_grounded_context("timing")
        assert "16:00" in ctx

    def test_accessibility_context_has_wheelchair(self):
        ctx = _build_grounded_context("accessibility")
        assert "wheelchair" in ctx.lower()

    def test_unknown_intent_empty_context(self):
        ctx = _build_grounded_context("random_nonsense")
        assert ctx == ""


class TestChatResponse:
    def test_route_redirect(self):
        reply, intent, grounded = get_chat_response("How do I navigate to the restroom?")
        assert intent == "route"
        assert "Route Planner" in reply
        assert grounded is True

    def test_prohibited_response(self):
        reply, intent, grounded = get_chat_response("What items are banned?")
        assert intent == "prohibited"
        assert grounded is True
        assert len(reply) > 20

    def test_timing_response(self):
        reply, intent, grounded = get_chat_response("What time does the match start?")
        assert intent == "timing"
        assert grounded is True

    def test_unknown_fallback(self):
        reply, intent, grounded = get_chat_response("Tell me about quantum physics")
        assert isinstance(reply, str)
        assert len(reply) > 0
