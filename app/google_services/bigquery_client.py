"""
google_services/bigquery_client.py
------------------------------------
BigQuery analytics client with mock fallback.

Design:
- In production: reads crowd analytics from BigQuery.
- In development: generates plausible historical data from a seeded RNG.
- Caches aggregation results for 60 seconds to avoid redundant scans.
"""

import logging
import random
import time
from typing import Any, Dict, List, Optional

from app.config import settings, ZONE_REGISTRY

logger = logging.getLogger(__name__)


class _MockBigQueryClient:
    """Generates realistic-looking analytics data without any GCP dependency."""

    def __init__(self) -> None:
        self._rng = random.Random(42)
        self._cache: Dict[str, tuple[float, Any]] = {}
        self._cache_ttl = 60

    def _cached(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and (time.time() - entry[0]) < self._cache_ttl:
            return entry[1]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = (time.time(), value)

    def get_historical_hotspots(self, top_n: int = 5) -> List[str]:
        """Returns the most frequently congested zones based on mock history."""
        cached = self._cached("hotspots")
        if cached:
            return cached

        zones = list(ZONE_REGISTRY.keys())
        weighted = sorted(
            zones,
            key=lambda z: ZONE_REGISTRY[z].get("capacity", 300),
            reverse=True,
        )
        result = [ZONE_REGISTRY[z]["name"] for z in weighted[:top_n]]
        self._set_cache("hotspots", result)
        return result

    def get_peak_density_history(self, zone_id: str) -> Dict[str, Any]:
        """Returns mock historical peak density for a zone."""
        return {
            "zone_id": zone_id,
            "avg_peak_density": self._rng.randint(55, 85),
            "max_peak_density": self._rng.randint(80, 98),
            "sample_count": self._rng.randint(200, 1000),
        }


# ── Client initialization ───────────────────────────────────────────────────
_client: Any = None
_mock_client = _MockBigQueryClient()
_using_mock = True

if settings.bigquery_enabled and settings.gcp_project_id:
    try:
        from google.cloud import bigquery
        _client = bigquery.Client(project=settings.gcp_project_id)
        _using_mock = False
        logger.info("BigQuery: Connected to project '%s'.", settings.gcp_project_id)
    except Exception as exc:
        logger.warning("BigQuery: Connection failed — using mock. Error: %s", exc)
else:
    logger.info("BigQuery: Running in mock mode (BIGQUERY_ENABLED=false).")


# ── Public API ───────────────────────────────────────────────────────────────

def get_historical_hotspots(top_n: int = 5) -> List[str]:
    """Returns the historically most congested zone names.

    Args:
        top_n: Maximum number of zones to return. Clamped to [1, 20]
               to prevent abuse.
    """
    top_n = max(1, min(20, int(top_n)))  # Sanitize input

    if _using_mock:
        return _mock_client.get_historical_hotspots(top_n)

    try:
        from google.cloud import bigquery as bq

        query = """
            SELECT zone_name, AVG(density) AS avg_density
            FROM `crowdpulse.density_history`
            GROUP BY zone_name
            ORDER BY avg_density DESC
            LIMIT @top_n
        """
        job_config = bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter("top_n", "INT64", top_n),
            ]
        )
        results = _client.query(query, job_config=job_config).result()
        return [row.zone_name for row in results]
    except Exception as exc:
        logger.error("BigQuery: Hotspots query failed — using mock. %s", exc)
        return _mock_client.get_historical_hotspots(top_n)


def get_peak_density_history(zone_id: str) -> Dict[str, Any]:
    """Returns peak density analytics for a zone.

    Args:
        zone_id: The zone identifier. Must be a valid key in ZONE_REGISTRY.
    """
    if _using_mock:
        return _mock_client.get_peak_density_history(zone_id)

    try:
        from google.cloud import bigquery as bq

        query = """
            SELECT
                zone_id,
                AVG(density) AS avg_peak_density,
                MAX(density) AS max_peak_density,
                COUNT(*) AS sample_count
            FROM `crowdpulse.density_history`
            WHERE zone_id = @zone_id
            GROUP BY zone_id
        """
        job_config = bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter("zone_id", "STRING", zone_id),
            ]
        )
        results = list(_client.query(query, job_config=job_config).result())
        if results:
            row = results[0]
            return {
                "zone_id": zone_id,
                "avg_peak_density": row.avg_peak_density,
                "max_peak_density": row.max_peak_density,
                "sample_count": row.sample_count,
            }
        return _mock_client.get_peak_density_history(zone_id)
    except Exception as exc:
        logger.error("BigQuery: Peak density query failed — using mock. %s", exc)
        return _mock_client.get_peak_density_history(zone_id)


def is_using_mock() -> bool:
    """Returns True if running in mock mode."""
    return _using_mock
