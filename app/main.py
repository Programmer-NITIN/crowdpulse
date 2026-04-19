"""
main.py
-------
FastAPI application factory for CrowdPulse AI.

Responsibilities:
  - Creates the FastAPI instance with conditional documentation.
  - Registers all API routers under appropriate prefixes.
  - Installs security middleware (CSP, HSTS, X-Frame-Options).
  - Configures CORS based on environment (wildcard in debug, strict in prod).
  - Mounts the static frontend for SPA serving.
  - Provides a startup/shutdown lifecycle hook.
"""

import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api import routes_health, routes_crowd, routes_navigation
from app.api import routes_assistant, routes_analytics, routes_auth
from app.google_services.cloud_logging import log_info, log_request

logger = logging.getLogger(__name__)


# ── Lifecycle ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup and shutdown hooks for the application."""
    log_info("CrowdPulse AI starting", {
        "version": settings.app_version,
        "debug": settings.debug,
        "services": {
            "gemini": bool(settings.gemini_api_key),
            "firestore": settings.firestore_enabled,
            "bigquery": settings.bigquery_enabled,
            "maps": settings.maps_enabled,
            "cloud_logging": settings.cloud_logging_enabled,
            "firebase_auth": settings.firebase_auth_enabled,
        },
    })
    yield
    log_info("CrowdPulse AI shutting down")


# ── App creation ─────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Intelligent crowd navigation platform for large-scale sporting venues.",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    lifespan=lifespan,
)


# ── Security headers middleware ──────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Injects production security headers on every response.

    Headers:
    - Content-Security-Policy: restricts resource origins.
    - X-Content-Type-Options: prevents MIME sniffing.
    - X-Frame-Options: prevents clickjacking.
    - Referrer-Policy: limits referrer leakage.
    - Strict-Transport-Security: enforces HTTPS in production.
    """
    start = time.monotonic()
    response: Response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(self), payment=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://maps.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://*.googleapis.com https://*.gstatic.com; "
        "connect-src 'self' https://*.googleapis.com; "
        "frame-ancestors 'none'"
    )

    if not settings.debug:
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )

    # Request logging
    latency_ms = (time.monotonic() - start) * 1000
    log_request(request.method, request.url.path, response.status_code, latency_ms)

    return response


# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(routes_health.router, tags=["Health"])
app.include_router(routes_crowd.router, tags=["Crowd Telemetry"])
app.include_router(routes_navigation.router, tags=["Navigation"])
app.include_router(routes_assistant.router, tags=["Event Assistant"])
app.include_router(routes_analytics.router, tags=["Staff Analytics"])
app.include_router(routes_auth.router, tags=["Authentication"])


# ── Static frontend ─────────────────────────────────────────────────────────
try:
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
except Exception:  # pylint: disable=broad-exception-caught
    logger.warning("Frontend directory not found — API-only mode.")
