"""
google_services/cloud_logging.py
----------------------------------
Google Cloud Logging integration with local console fallback.

Design:
- In production (Cloud Run): ships structured logs to Cloud Logging
  with proper severity levels, resource labels, and trace context.
- In development: outputs formatted, severity-coloured console logs.
- Provides a consistent API regardless of backend.
"""

import logging
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_cloud_logger: Any = None
_using_mock = True

if settings.cloud_logging_enabled and settings.gcp_project_id:
    try:
        from google.cloud import logging as cloud_logging
        client = cloud_logging.Client(project=settings.gcp_project_id)
        _cloud_logger = client.logger("crowdpulse-server")
        _using_mock = False
        logger.info("Cloud Logging: Connected to project '%s'.", settings.gcp_project_id)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Cloud Logging: Connection failed — using console. Error: %s", exc)
else:
    logger.info("Cloud Logging: Running in console mode (CLOUD_LOGGING_ENABLED=false).")


def log_info(message: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """Log an informational message."""
    if _cloud_logger and not _using_mock:
        _cloud_logger.log_struct(
            {"message": message, **(payload or {})},
            severity="INFO",
        )
    else:
        logger.info(message, extra=payload or {})


def log_warning(message: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """Log a warning."""
    if _cloud_logger and not _using_mock:
        _cloud_logger.log_struct(
            {"message": message, **(payload or {})},
            severity="WARNING",
        )
    else:
        logger.warning(message, extra=payload or {})


def log_error(
    message: str,
    error: Optional[Exception] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an error with optional exception context."""
    error_info = {}
    if error:
        error_info = {"error_type": type(error).__name__, "error_message": str(error)}

    if _cloud_logger and not _using_mock:
        _cloud_logger.log_struct(
            {"message": message, **error_info, **(payload or {})},
            severity="ERROR",
        )
    else:
        logger.error("%s %s", message, error_info, extra=payload or {})


def log_request(method: str, path: str, status_code: int, latency_ms: float) -> None:
    """Log an API request for monitoring."""
    payload = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2),
    }
    if _cloud_logger and not _using_mock:
        _cloud_logger.log_struct(
            {"message": f"{method} {path} → {status_code}", **payload},
            severity="INFO",
        )
    else:
        logger.info(
            "%s %s → %d (%.1fms)", method, path, status_code, latency_ms
        )


def is_using_mock() -> bool:
    """Returns True if running in console-only mode."""
    return _using_mock
