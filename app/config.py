"""
config.py
---------
Centralized application settings, zone definitions, and constants.

All environment variables are read through this module exclusively.
No other module reads from .env directly — this is the single source of truth
for configuration across the entire application.

Security notes:
- In production (DEBUG=false) set ALLOWED_ORIGINS to a comma-separated list of
  trusted frontend domains. Wildcard CORS is only permitted when DEBUG=true.
- Set DOCS_ENABLED=false before going live to hide /docs and /redoc.
- Never commit real API keys to source code or .env.example.
"""

import logging
from typing import Any, Dict, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# ── Logging Configuration ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("crowdpulse")


class Settings(BaseSettings):
    """Application-wide configuration backed by environment variables.

    All fields have safe defaults so the app can boot without any .env file.
    Google-service flags default to False — enabling them requires explicit opt-in.
    """

    app_name: str = "CrowdPulse AI"
    app_version: str = "1.0.0"
    debug: bool = False

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        """Accept flexible truthy strings for the DEBUG flag."""
        if isinstance(v, str):
            return v.lower() in ("true", "t", "1", "yes", "y", "on")
        return bool(v)

    # ── Security ──────────────────────────────────────────────────────────────
    allowed_origins_raw: str = ""
    docs_enabled: bool = True

    @field_validator("allowed_origins_raw", mode="before")
    @classmethod
    def parse_origins_raw(cls, v: Any) -> str:
        """Accept list or str from env; always normalize to str."""
        if isinstance(v, list):
            return ",".join(v)
        return str(v) if v else ""

    @property
    def allowed_origins(self) -> List[str]:
        """Returns the effective CORS origin list.

        - Debug mode  → ["*"] unless explicitly overridden.
        - Prod  mode  → parsed ALLOWED_ORIGINS; empty list blocks all CORS.
        """
        if self.allowed_origins_raw.strip():
            return [o.strip() for o in self.allowed_origins_raw.split(",") if o.strip()]
        if self.debug:
            return ["*"]
        return []

    # ── Gemini AI ─────────────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_timeout_seconds: int = 8

    # ── Google Cloud Platform ─────────────────────────────────────────────────
    gcp_project_id: str = ""
    firestore_enabled: bool = False
    bigquery_enabled: bool = False
    maps_api_key: str = ""
    maps_enabled: bool = False
    cloud_logging_enabled: bool = False

    # ── Firebase Authentication ───────────────────────────────────────────────
    firebase_credentials_path: str = ""
    firebase_auth_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Singleton instance — imported by all modules
settings = Settings()


# ─────────────────────────────────────────────────────────────────────────────
# Zone Registry
# Defines all physical zones in the venue graph.
# Add / remove zones here — no code changes needed elsewhere.
# ─────────────────────────────────────────────────────────────────────────────
ZONE_REGISTRY: Dict[str, Dict] = {
    "GA": {
        "name": "Gate A — North Entry",
        "type": "gate",
        "capacity": 600,
        "neighbors": {"C1": 55, "C2": 65},
        "accessible": True,
        "family_friendly": True,
        "coordinates": {"lat": 18.9388, "lng": 72.8258},
    },
    "GB": {
        "name": "Gate B — East Entry",
        "type": "gate",
        "capacity": 500,
        "neighbors": {"C1": 45, "C3": 75},
        "accessible": True,
        "family_friendly": True,
        "coordinates": {"lat": 18.9392, "lng": 72.8265},
    },
    "GC": {
        "name": "Gate C — South Entry",
        "type": "gate",
        "capacity": 400,
        "neighbors": {"C2": 55, "C3": 50},
        "accessible": True,
        "family_friendly": False,
        "coordinates": {"lat": 18.9380, "lng": 72.8270},
    },
    "GD": {
        "name": "Gate D — West VIP Entry",
        "type": "gate",
        "capacity": 300,
        "neighbors": {"C4": 40},
        "accessible": True,
        "family_friendly": True,
        "coordinates": {"lat": 18.9385, "lng": 72.8250},
    },
    "FC": {
        "name": "Food Court — Level 1",
        "type": "amenity",
        "capacity": 350,
        "neighbors": {"C1": 30, "C2": 70},
        "accessible": True,
        "family_friendly": True,
        "coordinates": {"lat": 18.9386, "lng": 72.8260},
    },
    "ST": {
        "name": "Main Stadium Bowl",
        "type": "venue",
        "capacity": 5000,
        "neighbors": {"C2": 100, "C3": 110, "C4": 90},
        "accessible": True,
        "family_friendly": True,
        "coordinates": {"lat": 18.9390, "lng": 72.8263},
    },
    "C1": {
        "name": "Corridor 1 — North-East",
        "type": "corridor",
        "capacity": 250,
        "neighbors": {"GA": 55, "GB": 45, "FC": 30},
        "accessible": True,
        "family_friendly": True,
        "coordinates": {"lat": 18.9389, "lng": 72.8261},
    },
    "C2": {
        "name": "Corridor 2 — North-South",
        "type": "corridor",
        "capacity": 250,
        "neighbors": {"GA": 65, "GC": 55, "FC": 70, "ST": 100},
        "accessible": False,
        "family_friendly": False,
        "coordinates": {"lat": 18.9384, "lng": 72.8264},
    },
    "C3": {
        "name": "Corridor 3 — East-South",
        "type": "corridor",
        "capacity": 200,
        "neighbors": {"GB": 75, "GC": 50, "ST": 110, "RR": 25, "MC": 35},
        "accessible": True,
        "family_friendly": True,
        "coordinates": {"lat": 18.9387, "lng": 72.8268},
    },
    "C4": {
        "name": "Corridor 4 — West VIP",
        "type": "corridor",
        "capacity": 150,
        "neighbors": {"GD": 40, "ST": 90, "MS": 30},
        "accessible": True,
        "family_friendly": True,
        "coordinates": {"lat": 18.9386, "lng": 72.8253},
    },
    "RR": {
        "name": "Main Restroom Block",
        "type": "restroom",
        "capacity": 60,
        "neighbors": {"C3": 25},
        "accessible": True,
        "family_friendly": True,
        "coordinates": {"lat": 18.9391, "lng": 72.8271},
    },
    "MC": {
        "name": "Medical Centre",
        "type": "medical",
        "capacity": 30,
        "neighbors": {"C3": 35},
        "accessible": True,
        "family_friendly": True,
        "coordinates": {"lat": 18.9393, "lng": 72.8269},
    },
    "MS": {
        "name": "Merchandise Store",
        "type": "amenity",
        "capacity": 120,
        "neighbors": {"C4": 30},
        "accessible": True,
        "family_friendly": True,
        "coordinates": {"lat": 18.9383, "lng": 72.8252},
    },
}

# ── Peak Hour Windows (24h format) ───────────────────────────────────────────
PEAK_HOUR_WINDOWS = [
    (8, 10),   # Morning rush
    (12, 14),  # Lunch break
    (17, 21),  # Evening match window
]

# ── Density Thresholds → Status Labels ───────────────────────────────────────
DENSITY_STATUS_MAP = [
    (80, "CRITICAL"),
    (60, "HIGH"),
    (35, "MEDIUM"),
    (0, "LOW"),
]
