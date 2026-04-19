# Google Services Integration Guide

CrowdPulse AI integrates **7 Google Cloud services** in a production-ready, mock-first architecture that allows the platform to run both locally (with zero GCP credentials) and in production (fully connected).

---

## Architecture: Mock-First Design

Every Google service follows the same pattern:

```python
# 1. Try to connect to the live service
if settings.service_enabled and settings.credentials:
    _client = LiveServiceClient(credentials)
    _using_mock = False

# 2. Fall back to deterministic mock
else:
    _using_mock = True

# 3. Public API always works — callers never know which backend
def public_function():
    if _using_mock:
        return _mock_client.deterministic_response()
    try:
        return _client.live_api_call()
    except Exception:
        return _mock_client.deterministic_response()  # Graceful degradation
```

This guarantees **zero-downtime** — even if Google Cloud is unreachable.

---

## Service 1: Gemini AI (Generative AI)

**Purpose:** Natural language explanations and staff advisory.

| Aspect | Detail |
|--------|--------|
| **SDK** | `google-generativeai` |
| **Used in** | `ai_engine/explainer.py`, `ai_engine/chatbot.py`, `ai_engine/staff_advisor.py` |
| **Config** | `GEMINI_API_KEY`, `GEMINI_MODEL` |
| **Mock fallback** | Deterministic template responses |

**Integration points:**
- **Route Explainer**: Takes pre-computed Dijkstra route and generates a data-grounded, 3-sentence explanation.
- **Event Chatbot**: 12-intent classifier handles intent deterministically; Gemini only phrases the response using grounded venue data.
- **Staff Advisor**: Generates crowd management recommendations, triage alerts, and operational briefings from live density data.

**Key design decision:** Gemini is *never* used for routing decisions — only for explanation and phrasing. This ensures deterministic, auditable navigation.

---

## Service 2: Cloud Firestore

**Purpose:** Real-time session persistence and crowd snapshots.

| Aspect | Detail |
|--------|--------|
| **SDK** | `google-cloud-firestore` |
| **Used in** | `google_services/firestore_client.py`, `api/routes_navigation.py` |
| **Config** | `FIRESTORE_ENABLED`, `GCP_PROJECT_ID` |
| **Mock fallback** | Bounded OrderedDict (500 entries, LRU eviction) |

**Collections:**
- `navigation_sessions`: Stores route computation results with user ID, path, and timestamp.
- `crowd_snapshots`: Periodic density data for historical analysis.

---

## Service 3: BigQuery Analytics

**Purpose:** Historical crowd density analytics and hotspot detection.

| Aspect | Detail |
|--------|--------|
| **SDK** | `google-cloud-bigquery` |
| **Used in** | `google_services/bigquery_client.py`, `api/routes_analytics.py` |
| **Config** | `BIGQUERY_ENABLED`, `GCP_PROJECT_ID` |
| **Mock fallback** | Seeded RNG (seed=42) for reproducible analytics |

**Queries (parameterized — no SQL injection):**
- `get_historical_hotspots()`: Top-N most congested zones by average density.
- `get_peak_density_history()`: Peak density statistics for a specific zone.

---

## Service 4: Google Maps Platform

**Purpose:** Walking distance calculation and coordinate-based waypoints.

| Aspect | Detail |
|--------|--------|
| **SDK** | `googlemaps` |
| **Used in** | `google_services/maps_client.py`, `api/routes_navigation.py` |
| **Config** | `MAPS_ENABLED`, `MAPS_API_KEY` |
| **Mock fallback** | Pre-configured distances from venue graph (ZONE_REGISTRY) |

**API calls:**
- `Distance Matrix API`: Walking distances between adjacent zones.
- `Zone coordinates`: GPS lat/lng for all 13 venue zones.
- `Route waypoints`: Ordered list of coordinates for map rendering.

---

## Service 5: Cloud Logging

**Purpose:** Structured logging with severity levels and request tracing.

| Aspect | Detail |
|--------|--------|
| **SDK** | `google-cloud-logging` |
| **Used in** | `google_services/cloud_logging.py`, `app/main.py` |
| **Config** | `CLOUD_LOGGING_ENABLED`, `GCP_PROJECT_ID` |
| **Mock fallback** | Python stdlib `logging` with formatted console output |

**Log types:**
- `log_info()`: Informational events (startup, navigation computed).
- `log_warning()`: Degraded service states (Gemini unavailable).
- `log_error()`: Failures with exception context.
- `log_request()`: HTTP request metrics (method, path, status, latency).

---

## Service 6: Firebase Authentication

**Purpose:** User identity verification via Firebase ID tokens.

| Aspect | Detail |
|--------|--------|
| **SDK** | `firebase-admin` |
| **Used in** | `google_services/firebase_auth.py`, `api/routes_auth.py` |
| **Config** | `FIREBASE_AUTH_ENABLED`, `FIREBASE_CREDENTIALS_PATH` |
| **Mock fallback** | Accepts `mock-<uid>` tokens with synthetic claims |

**Token verification flow:**
1. Client sends `Authorization: Bearer <token>` header.
2. Server verifies token with Firebase Admin SDK.
3. Returns decoded claims (uid, email, name).
4. In mock mode: any `mock-*` token is accepted for testing.

---

## Service 7: Cloud Run (Deployment)

**Purpose:** Serverless container hosting with auto-scaling.

| Aspect | Detail |
|--------|--------|
| **Config** | `Dockerfile` (multi-stage, non-root), `.gcloudignore` |
| **Health check** | `GET /health` for readiness probes |
| **Port** | `8080` (Cloud Run default) |

**Deployment command:**
```bash
gcloud run deploy crowdpulse \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DEBUG=false"
```

**Dockerfile features:**
- Multi-stage build (builder + runtime).
- Non-root user (`appuser`) for container security.
- Layer caching for fast rebuilds.
- Health check via `curl`.

---

## Environment Variables

```env
# Gemini AI
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.0-flash

# Firestore
FIRESTORE_ENABLED=true
GCP_PROJECT_ID=your-project-id

# BigQuery
BIGQUERY_ENABLED=true

# Google Maps
MAPS_ENABLED=true
MAPS_API_KEY=your-maps-key

# Cloud Logging
CLOUD_LOGGING_ENABLED=true

# Firebase Auth
FIREBASE_AUTH_ENABLED=true
FIREBASE_CREDENTIALS_PATH=path/to/serviceAccount.json
```

---

## Testing

All 7 services are tested in `tests/test_google_services.py`:

```bash
pytest tests/test_google_services.py -v
```

The test suite verifies:
- ✅ Mock fallback returns correct data schemas.
- ✅ Firestore CRUD operations (store, retrieve, list, eviction).
- ✅ BigQuery analytics data within expected ranges.
- ✅ Maps distance calculations and coordinate lookups.
- ✅ Cloud Logging doesn't raise on any severity level.
- ✅ Firebase Auth accepts mock tokens and rejects invalid ones.
