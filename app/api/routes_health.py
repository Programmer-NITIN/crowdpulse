"""
api/routes_health.py
--------------------
Health and readiness endpoints for monitoring and container orchestration.
"""

from fastapi import APIRouter

from app.config import settings
from app.google_services import firestore_client, bigquery_client, maps_client, cloud_logging

router = APIRouter()


@router.get("/health")
async def health_check():
    """Returns the service health status and backend configuration.

    Cloud Run uses this endpoint for readiness probes.
    """
    return {
        "status": "ok",
        "version": settings.app_version,
        "app": settings.app_name,
        "services": {
            "gemini": "configured" if settings.gemini_api_key else "mock",
            "firestore": "live" if not firestore_client.is_using_mock() else "mock",
            "bigquery": "live" if not bigquery_client.is_using_mock() else "mock",
            "maps": "live" if not maps_client.is_using_mock() else "mock",
            "cloud_logging": "live" if not cloud_logging.is_using_mock() else "mock",
        },
    }
