"""
tests/test_security.py
-----------------------
Validates security hardening:
  - Security headers present on every response
  - CORS origin list reflects debug mode
  - Rate limiter returns 429 after threshold is exceeded
  - Input validation rejects oversized / empty payloads
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=True)

_VALID_NAV_PAYLOAD = {
    "user_id": "test-user",
    "current_zone": "GA",
    "destination": "ST",
    "priority": "fast_exit",
}

_VALID_CHAT_PAYLOAD = {
    "user_id": "test-user",
    "message": "What items are prohibited?",
}


class TestSecurityHeaders:
    def _get_headers(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        return resp.headers

    def test_x_content_type_options(self):
        assert self._get_headers().get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self):
        assert self._get_headers().get("x-frame-options") == "DENY"

    def test_referrer_policy(self):
        assert self._get_headers().get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_content_security_policy_present(self):
        csp = self._get_headers().get("content-security-policy", "")
        assert "default-src" in csp

    def test_csp_blocks_frames(self):
        csp = self._get_headers().get("content-security-policy", "")
        assert "frame-ancestors 'none'" in csp

    def test_csp_allows_google_fonts(self):
        csp = self._get_headers().get("content-security-policy", "")
        assert "fonts.googleapis.com" in csp

    def test_csp_allows_google_maps(self):
        csp = self._get_headers().get("content-security-policy", "")
        assert "maps.googleapis.com" in csp

    def test_permissions_policy_restricts_camera(self):
        pp = self._get_headers().get("permissions-policy", "")
        assert "camera=()" in pp

    def test_permissions_policy_restricts_microphone(self):
        pp = self._get_headers().get("permissions-policy", "")
        assert "microphone=()" in pp

    def test_permissions_policy_allows_geolocation_self(self):
        pp = self._get_headers().get("permissions-policy", "")
        assert "geolocation=(self)" in pp

    def test_x_permitted_cross_domain_policies(self):
        assert self._get_headers().get("x-permitted-cross-domain-policies") == "none"


class TestCorsConfiguration:
    def test_debug_mode_returns_wildcard(self):
        from app.config import Settings
        s = Settings(debug=True, allowed_origins_raw="")
        assert s.allowed_origins == ["*"]

    def test_prod_mode_no_origins_returns_empty(self):
        from app.config import Settings
        s = Settings(debug=False, allowed_origins_raw="")
        assert s.allowed_origins == []

    def test_explicit_origins_respected(self):
        from app.config import Settings
        s = Settings(debug=True, allowed_origins_raw="https://example.com,https://app.example.com")
        assert s.allowed_origins == ["https://example.com", "https://app.example.com"]

    def test_origins_whitespace_stripped(self):
        from app.config import Settings
        s = Settings(debug=False, allowed_origins_raw="  https://a.com , https://b.com  ")
        assert s.allowed_origins == ["https://a.com", "https://b.com"]


class TestNavigationRateLimit:
    _base_ip = "192.168.99."

    def test_rate_limit_triggers_after_threshold(self):
        from app.middleware.rate_limiter import navigation_rate_limit
        navigation_rate_limit.store.clear()

        headers = {"X-Forwarded-For": f"{self._base_ip}10"}
        hit_429 = False
        for _ in range(12):
            resp = client.post("/navigate/suggest", json=_VALID_NAV_PAYLOAD, headers=headers)
            if resp.status_code == 429:
                hit_429 = True
                break
        assert hit_429, "Expected HTTP 429 after exceeding rate limit threshold"

    def test_rate_limit_response_has_retry_after(self):
        headers = {"X-Forwarded-For": f"{self._base_ip}11"}
        for _ in range(12):
            resp = client.post("/navigate/suggest", json=_VALID_NAV_PAYLOAD, headers=headers)
            if resp.status_code == 429:
                assert "retry-after" in resp.headers
                return
        pytest.fail("Rate limit was never triggered")


class TestChatRateLimit:
    def test_chat_rate_limit_triggers(self):
        from app.middleware.rate_limiter import chat_rate_limit
        chat_rate_limit.store.clear()

        headers = {"X-Forwarded-For": "192.168.100.10"}
        hit_429 = False
        for _ in range(22):
            resp = client.post("/assistant/chat", json=_VALID_CHAT_PAYLOAD, headers=headers)
            if resp.status_code == 429:
                hit_429 = True
                break
        assert hit_429, "Expected HTTP 429 after exceeding chat rate limit"


class TestChatInputValidation:
    def test_empty_message_rejected(self):
        resp = client.post("/assistant/chat", json={**_VALID_CHAT_PAYLOAD, "message": ""})
        assert resp.status_code == 422

    def test_whitespace_only_message_rejected(self):
        resp = client.post("/assistant/chat", json={**_VALID_CHAT_PAYLOAD, "message": "   "})
        assert resp.status_code == 422

    def test_oversized_message_rejected(self):
        resp = client.post("/assistant/chat", json={**_VALID_CHAT_PAYLOAD, "message": "x" * 501})
        assert resp.status_code == 422

    def test_maximum_valid_message_accepted(self):
        resp = client.post("/assistant/chat", json={**_VALID_CHAT_PAYLOAD, "message": "q" * 500})
        assert resp.status_code != 422

    def test_missing_user_id_rejected(self):
        resp = client.post("/assistant/chat", json={"message": "Hello"})
        assert resp.status_code == 422


class TestNavigationInputValidation:
    _headers = {"X-Forwarded-For": "192.168.101.10"}
    _url = "/navigate/suggest"

    def test_zone_id_too_long_rejected(self):
        payload = {**_VALID_NAV_PAYLOAD, "current_zone": "Z" * 33}
        resp = client.post(self._url, json=payload, headers=self._headers)
        assert resp.status_code == 422

    def test_user_id_too_long_rejected(self):
        payload = {**_VALID_NAV_PAYLOAD, "user_id": "u" * 65}
        resp = client.post(self._url, json=payload, headers=self._headers)
        assert resp.status_code == 422

    def test_too_many_constraints_rejected(self):
        payload = {**_VALID_NAV_PAYLOAD, "constraints": ["c"] * 6}
        resp = client.post(self._url, json=payload, headers=self._headers)
        assert resp.status_code == 422

    def test_empty_user_id_rejected(self):
        payload = {**_VALID_NAV_PAYLOAD, "user_id": ""}
        resp = client.post(self._url, json=payload, headers=self._headers)
        assert resp.status_code == 422

    def test_user_note_too_long_rejected(self):
        payload = {**_VALID_NAV_PAYLOAD, "user_note": "n" * 257}
        resp = client.post(self._url, json=payload, headers=self._headers)
        assert resp.status_code == 422

    def test_empty_destination_rejected(self):
        payload = {**_VALID_NAV_PAYLOAD, "destination": ""}
        resp = client.post(self._url, json=payload, headers=self._headers)
        assert resp.status_code == 422
