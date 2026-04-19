"""
tests/test_accessibility.py
-----------------------------
Smoke tests for WCAG 2.1 AA compliance indicators in the HTML frontend.
"""

import os

# Read the HTML once at module load
_FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
with open(_FRONTEND_PATH, encoding="utf-8") as f:
    _HTML = f.read()


class TestSkipNavigation:
    def test_skip_link_exists(self):
        assert 'class="skip-link"' in _HTML

    def test_skip_link_targets_main(self):
        assert 'href="#main-content"' in _HTML

    def test_main_content_id_exists(self):
        assert 'id="main-content"' in _HTML


class TestAriaLiveRegions:
    def test_sr_announcer_exists(self):
        assert 'id="sr-announcer"' in _HTML
        assert 'aria-live="polite"' in _HTML

    def test_insight_banner_live(self):
        assert 'id="insights-badge"' in _HTML

    def test_form_error_assertive(self):
        assert 'id="form-error"' in _HTML
        assert 'aria-live="assertive"' in _HTML

    def test_chat_feed_live(self):
        assert 'id="chat-feed"' in _HTML
        assert 'aria-live="polite"' in _HTML


class TestAriaLabels:
    def test_main_navigation_label(self):
        assert 'aria-label="Main Navigation"' in _HTML

    def test_main_content_label(self):
        assert 'aria-label="Venue Intelligence Console"' in _HTML

    def test_route_selection_label(self):
        assert 'aria-label="Route Selection"' in _HTML

    def test_route_findings_label(self):
        assert 'aria-label="Route Findings"' in _HTML

    def test_route_timeline_label(self):
        assert 'aria-label="Route stages"' in _HTML

    def test_scoring_factors_label(self):
        assert 'aria-label="AI scoring factors"' in _HTML

    def test_staff_operations_label(self):
        assert 'aria-label="Staff Operations Control"' in _HTML

    def test_map_img_role(self):
        assert 'role="img"' in _HTML

    def test_chat_dialog_role(self):
        assert 'role="dialog"' in _HTML

    def test_chat_assistant_label(self):
        assert 'aria-label="Open Event Assistant"' in _HTML

    def test_chat_close_label(self):
        assert 'aria-label="Close Assistant"' in _HTML

    def test_chat_input_label(self):
        assert 'aria-label="Message the assistant"' in _HTML


class TestFormAccessibility:
    def test_origin_zone_has_label(self):
        assert 'for="current_zone"' in _HTML

    def test_destination_has_label(self):
        assert 'for="destination"' in _HTML

    def test_priority_has_label(self):
        assert 'for="priority"' in _HTML

    def test_origin_has_describedby(self):
        assert 'aria-describedby="current_zone_help"' in _HTML

    def test_destination_has_describedby(self):
        assert 'aria-describedby="destination_help"' in _HTML

    def test_fieldset_legends_exist(self):
        assert '<legend class="sr-only">' in _HTML

    def test_chat_input_maxlength(self):
        assert 'maxlength="500"' in _HTML


class TestProgressBars:
    def test_density_progressbar(self):
        assert 'id="bar-density"' in _HTML
        assert 'role="progressbar"' in _HTML

    def test_trend_progressbar(self):
        assert 'id="bar-trend"' in _HTML

    def test_event_progressbar(self):
        assert 'id="bar-event"' in _HTML

    def test_progressbar_min_max(self):
        assert 'aria-valuemin="0"' in _HTML
        assert 'aria-valuemax="100"' in _HTML


class TestHeadingHierarchy:
    def test_single_h1(self):
        count = _HTML.count("<h1")
        assert count == 1, f"Expected 1 <h1>, found {count}"

    def test_h1_has_id(self):
        assert 'id="hero-title"' in _HTML


class TestSemanticsAndSEO:
    def test_lang_attribute(self):
        assert '<html lang="en">' in _HTML

    def test_meta_description(self):
        assert 'name="description"' in _HTML

    def test_title_tag(self):
        assert "<title>" in _HTML
        assert "CrowdPulse" in _HTML

    def test_meta_viewport(self):
        assert 'name="viewport"' in _HTML

    def test_google_fonts_loaded(self):
        assert "fonts.googleapis.com" in _HTML


class TestReducedMotionCSS:
    """Verify the CSS file includes prefers-reduced-motion support."""

    _CSS_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "css", "style.css")

    def test_reduced_motion_media_query(self):
        with open(self._CSS_PATH, encoding="utf-8") as f:
            css = f.read()
        assert "prefers-reduced-motion" in css

    def test_focus_visible_styles(self):
        with open(self._CSS_PATH, encoding="utf-8") as f:
            css = f.read()
        assert "focus-visible" in css
