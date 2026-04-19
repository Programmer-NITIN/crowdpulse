"""
tests/test_cloud_logging.py
----------------------------
Tests for the Google Cloud Logging client with console fallback.
"""

from app.google_services.cloud_logging import (
    log_info,
    log_warning,
    log_error,
    log_request,
    is_using_mock,
)


class TestCloudLogging:
    def test_is_using_mock(self):
        assert is_using_mock() is True

    def test_log_info_no_crash(self):
        log_info("Test info message")

    def test_log_info_with_payload(self):
        log_info("Test info", {"key": "value"})

    def test_log_warning_no_crash(self):
        log_warning("Test warning")

    def test_log_warning_with_payload(self):
        log_warning("Test warning", {"severity": "low"})

    def test_log_error_no_crash(self):
        log_error("Test error")

    def test_log_error_with_exception(self):
        log_error("Test error", error=ValueError("test exception"))

    def test_log_error_with_payload(self):
        log_error("Test error", payload={"context": "unit_test"})

    def test_log_request_no_crash(self):
        log_request("GET", "/health", 200, 12.5)

    def test_log_request_post(self):
        log_request("POST", "/navigate/suggest", 200, 45.2)

    def test_log_request_error_status(self):
        log_request("POST", "/navigate/suggest", 500, 100.0)


class TestLoggingResilience:
    """Verify logging never raises exceptions even with unusual inputs."""

    def test_empty_message(self):
        log_info("")

    def test_unicode_message(self):
        log_info("Test with émojis 🏟️⚡🔥")

    def test_large_payload(self):
        log_info("Large payload test", {"data": "x" * 10000})

    def test_none_payload(self):
        log_info("None payload", None)
