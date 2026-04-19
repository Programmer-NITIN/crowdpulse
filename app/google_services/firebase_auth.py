"""
google_services/firebase_auth.py
----------------------------------
Firebase Authentication token verification with mock fallback.

Design:
- In production: verifies Firebase ID tokens using firebase-admin SDK.
- In development: accepts a mock token header for testing.
- Provides a dependency function for FastAPI route injection.
"""

import logging
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_firebase_app: Any = None
_using_mock = True

if settings.firebase_auth_enabled and settings.firebase_credentials_path:
    try:
        import firebase_admin  # pylint: disable=import-outside-toplevel
        from firebase_admin import credentials  # pylint: disable=import-outside-toplevel

        cred = credentials.Certificate(settings.firebase_credentials_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        _using_mock = False
        logger.info("Firebase Auth: Initialized with service account.")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Firebase Auth: Init failed — using mock. Error: %s", exc)
else:
    logger.info("Firebase Auth: Running in mock mode (FIREBASE_AUTH_ENABLED=false).")


def verify_token(id_token: str) -> Optional[Dict[str, Any]]:
    """Verifies a Firebase ID token and returns the decoded claims.

    In mock mode:
    - Any token starting with 'mock-' is accepted.
    - Returns a synthetic claims dict with uid and email.
    """
    if _using_mock:
        if id_token.startswith("mock-"):
            return {
                "uid": id_token.replace("mock-", ""),
                "email": f"{id_token.replace('mock-', '')}@mock.crowdpulse.dev",
                "name": "Mock User",
            }
        return None

    try:
        from firebase_admin import auth  # pylint: disable=import-outside-toplevel
        decoded = auth.verify_id_token(id_token)
        return decoded
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Firebase Auth: Token verification failed: %s", exc)
        return None


def is_using_mock() -> bool:
    """Returns True if running in mock mode."""
    return _using_mock
