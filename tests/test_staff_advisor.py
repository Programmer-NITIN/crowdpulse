"""
tests/test_staff_advisor.py
----------------------------
Tests for the Gemini-powered staff AI advisor.
"""

from app.ai_engine.staff_advisor import (
    generate_recommendations,
    triage_alert,
    generate_briefing,
    _fallback_recommendations,
    _fallback_briefing,
)
from app.config import ZONE_REGISTRY


class TestRecommendations:
    def _make_density_map(self, default=50):
        return {z: default for z in ZONE_REGISTRY}

    def test_returns_list(self):
        recs = generate_recommendations(self._make_density_map())
        assert isinstance(recs, list)
        assert len(recs) >= 1

    def test_returns_strings(self):
        recs = generate_recommendations(self._make_density_map())
        for r in recs:
            assert isinstance(r, str)
            assert len(r) > 5

    def test_critical_zones_generate_recommendations(self):
        dm = self._make_density_map(40)
        dm["GA"] = 90
        dm["FC"] = 85
        recs = generate_recommendations(dm)
        assert len(recs) >= 1

    def test_all_low_returns_nominal(self):
        recs = generate_recommendations(self._make_density_map(20))
        assert len(recs) >= 1


class TestTriageAlert:
    def test_returns_string(self):
        dm = {z: 50 for z in ZONE_REGISTRY}
        result = triage_alert("GA", 85, dm)
        assert isinstance(result, str)
        assert len(result) > 10

    def test_mentions_zone(self):
        dm = {z: 50 for z in ZONE_REGISTRY}
        result = triage_alert("GA", 90, dm)
        assert "Gate A" in result or "GA" in result

    def test_critical_severity(self):
        dm = {z: 50 for z in ZONE_REGISTRY}
        result = triage_alert("FC", 95, dm)
        assert isinstance(result, str)


class TestBriefing:
    def test_returns_string(self):
        dm = {z: 50 for z in ZONE_REGISTRY}
        result = generate_briefing(dm)
        assert isinstance(result, str)
        assert len(result) > 10


class TestFallbacks:
    def test_fallback_recommendations_critical(self):
        dm = {z: 40 for z in ZONE_REGISTRY}
        dm["GA"] = 85
        recs = _fallback_recommendations(dm)
        assert any("CRITICAL" in r for r in recs)

    def test_fallback_recommendations_warning(self):
        dm = {z: 40 for z in ZONE_REGISTRY}
        dm["FC"] = 65
        recs = _fallback_recommendations(dm)
        assert any("WARNING" in r for r in recs)

    def test_fallback_recommendations_nominal(self):
        dm = {z: 20 for z in ZONE_REGISTRY}
        recs = _fallback_recommendations(dm)
        assert any("normal" in r.lower() for r in recs)

    def test_fallback_briefing_critical(self):
        dm = {z: 40 for z in ZONE_REGISTRY}
        dm["GA"] = 85
        briefing = _fallback_briefing(dm)
        assert "ALERT" in briefing

    def test_fallback_briefing_high(self):
        dm = {z: 40 for z in ZONE_REGISTRY}
        dm["GA"] = 65
        briefing = _fallback_briefing(dm)
        assert "NOTE" in briefing

    def test_fallback_briefing_nominal(self):
        dm = {z: 20 for z in ZONE_REGISTRY}
        briefing = _fallback_briefing(dm)
        assert "normal" in briefing.lower()
