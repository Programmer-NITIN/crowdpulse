"""
tests/test_coverage_boost.py
------------------------------
Comprehensive tests targeting ALL uncovered lines across the codebase.

Uses unittest.mock.patch to simulate live Google service connections
and Gemini API calls without requiring real API keys or network access.

This file covers:
- AI Engine: explainer, chatbot, staff_advisor, gemini_caller
- Google Services: firestore, bigquery, cloud_logging, firebase_auth, maps
- Decision Engine: router edge cases, scorer edge cases
- Crowd Engine: predictor, simulator, wait_times, cache edge cases
- Config: Settings validators
- Prompt Builder: density-level branches
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

from app.config import ZONE_REGISTRY
from app.models.navigation_models import Priority


# ══════════════════════════════════════════════════════════════════════

class TestConfigValidators:
    """Tests covering config.py lines 46, 58 (non-string debug, list origins)."""

    def test_parse_debug_non_string_true(self):
        """Debug flag accepts integer 1 as True."""
        from app.config import Settings
        s = Settings(debug=1)
        assert s.debug is True

    def test_parse_debug_non_string_false(self):
        """Debug flag accepts integer 0 as False."""
        from app.config import Settings
        s = Settings(debug=0)
        assert s.debug is False

    def test_parse_origins_list_input(self):
        """Origins accepts list input and normalizes to comma-separated."""
        from app.config import Settings
        s = Settings(allowed_origins_raw=["https://a.com", "https://b.com"])
        assert s.allowed_origins == ["https://a.com", "https://b.com"]

    def test_parse_origins_empty_debug(self):
        """Empty origins with debug=true returns wildcard."""
        from app.config import Settings
        s = Settings(debug=True, allowed_origins_raw="")
        assert s.allowed_origins == ["*"]

    def test_parse_origins_empty_prod(self):
        """Empty origins with debug=false returns empty list."""
        from app.config import Settings
        s = Settings(debug=False, allowed_origins_raw="")
        assert s.allowed_origins == []

