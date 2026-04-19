# CrowdPulse AI

**Intelligent Crowd Navigation Platform for Large-Scale Sporting Venues**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

CrowdPulse AI is a production-grade, AI-augmented crowd management system designed to transform the physical event experience at large-scale sporting venues. It combines **deterministic pathfinding** (Dijkstra's algorithm) with **Gemini AI explanations** to deliver real-time, crowd-aware navigation that is accurate, explainable, and safe.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (SPA)                      │
│   Premium glassmorphism UI • WCAG 2.1 AA • Chat widget  │
└──────────────┬──────────────────────────────┬───────────┘
               │ REST API                     │ WebSocket-ready
┌──────────────▼──────────────────────────────▼───────────┐
│                    FastAPI Backend                       │
│  Security Headers • Rate Limiting • Input Validation    │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ Crowd Engine │  │  Decision   │  │   AI Engine     │ │
│  │  Simulator   │  │   Engine    │  │  Gemini-powered │ │
│  │  Predictor   │  │  Scorer     │  │  Chatbot        │ │
│  │  Wait Times  │  │  Dijkstra   │  │  Staff Advisor  │ │
│  │  TTL Cache   │  │  Router     │  │  Explainer      │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────┤
│              Google Cloud Service Layer                  │
│  Firestore • BigQuery • Maps • Gemini • Cloud Logging   │
│  Firebase Auth • Cloud Run  (all with mock fallbacks)   │
└─────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Deterministic-first routing** | Dijkstra computes all routes — AI never makes navigation decisions |
| **Mock-first architecture** | Every Google service has an in-process mock — app runs with zero API keys |
| **TTL-cached density** | 2-second cache prevents redundant computation under high request volume |
| **Grounded chatbot** | Intent is classified deterministically; Gemini only phrases pre-resolved facts |
| **Sliding-window rate limiting** | Per-IP deque-based counters with configurable thresholds per route |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- pip

### Local Development (No API Keys Required)

```bash
# Clone and enter project
cd CrowdPulse

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload --port 8000
```

Visit **http://localhost:8000** for the full UI, or **http://localhost:8000/docs** for the Swagger API explorer.

### With Google Cloud Services (Optional)

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# GEMINI_API_KEY=your-key
# GCP_PROJECT_ID=your-project

# Run with live services
uvicorn app.main:app --reload --port 8000
```

---

## 📡 API Endpoints

| Method | Path | Description | Rate Limit |
|--------|------|-------------|------------|
| `GET` | `/health` | Service health & backend status | — |
| `GET` | `/crowd/status` | Live density for all 13 zones | 30/min |
| `GET` | `/crowd/predict` | 30-min density prediction per zone | 30/min |
| `GET` | `/crowd/wait-times` | Service wait times (gates, food, etc.) | 30/min |
| `POST` | `/navigate/suggest` | Compute optimal route | 10/min |
| `POST` | `/assistant/chat` | Grounded AI Event Assistant | 20/min |
| `GET` | `/analytics/dashboard` | Staff operations dashboard | 15/min |
| `GET` | `/auth/verify` | Firebase token verification | — |

---

## 🔒 Security Implementation

- **Content Security Policy** — restricts script/style/font/image origins
- **HTTP Strict Transport Security** — enforces HTTPS in production
- **X-Frame-Options: DENY** — prevents clickjacking
- **X-Content-Type-Options: nosniff** — prevents MIME sniffing
- **Referrer-Policy: strict-origin-when-cross-origin** — limits referrer leakage
- **Permissions-Policy** — disables camera, microphone; self-only geolocation
- **X-Permitted-Cross-Domain-Policies: none** — prevents Flash/PDF cross-domain reads
- **Sliding-window rate limiting** — per-IP, per-route thresholds
- **Parameterized SQL queries** — no string interpolation in BigQuery calls
- **Pydantic input validation** — bounded string lengths, enum constraints
- **Non-root Docker execution** — container runs as `appuser`

See [SECURITY.md](SECURITY.md) for full details.

---

## ♿ Accessibility (WCAG 2.1 AA)

- Skip-to-main-content link
- Full ARIA labeling (landmarks, roles, live regions)
- Keyboard navigable (all interactive elements)
- `focus-visible` outlines on every focusable element
- `prefers-reduced-motion` media query disables animations
- Screen reader announcements via `aria-live="polite"` announcer
- Form labels, fieldset legends, and describedby associations
- Single `<h1>` with proper heading hierarchy
- Semantic HTML5 throughout

See [ACCESSIBILITY.md](ACCESSIBILITY.md) for full details.

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/test_security.py -v
pytest tests/test_accessibility.py -v
pytest tests/test_performance.py -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Test Categories (302 tests, 81% coverage)

| File | Tests | Coverage |
|------|-------|----------|
| `test_api.py` | 55+ | All 6 API endpoint groups |
| `test_security.py` | 30+ | Headers, CORS, rate limiting, input validation |
| `test_crowd_engine.py` | 45+ | Simulator, predictor, cache, wait times |
| `test_decision_engine.py` | 30+ | Scorer, Dijkstra router, edge costs |
| `test_chatbot.py` | 25+ | Intent classification, grounded context |
| `test_accessibility.py` | 35+ | ARIA, skip-nav, headings, reduced-motion |
| `test_google_services.py` | 35+ | All 7 Google services mock verification |
| `test_analytics.py` | 10+ | Staff dashboard structure |
| `test_maps.py` | 10+ | Distance calculations, waypoints |
| `test_integration.py` | 12+ | Multi-service pipelines |
| `test_auth.py` | 10+ | Firebase Auth mock/live |
| `test_cloud_logging.py` | 15+ | Logging resilience |
| `test_staff_advisor.py` | 15+ | AI advisor fallbacks |
| `test_performance.py` | 10+ | Latency benchmarks, throughput |

---

## ☁️ Google Cloud Integration (7 Services)

| # | Service | Usage | Mock Fallback |
|---|---------|-------|---------------|
| 1 | **Gemini AI** | Route explanation, chatbot phrasing, staff advisor | Deterministic text |
| 2 | **Cloud Firestore** | Navigation session persistence | Bounded OrderedDict |
| 3 | **BigQuery** | Historical hotspot analytics | Seeded RNG data |
| 4 | **Google Maps** | Walking distances, coordinates | Zone registry distances |
| 5 | **Cloud Logging** | Structured request/error logging | Console logger |
| 6 | **Firebase Auth** | User token verification | `mock-*` token acceptance |
| 7 | **Cloud Run** | Container deployment | Local uvicorn |

See [GOOGLE_SERVICES.md](GOOGLE_SERVICES.md) for detailed integration documentation.

---

## 🐳 Docker Deployment

```bash
# Build the image
docker build -t crowdpulse-ai .

# Run locally
docker run -p 8000:8000 crowdpulse-ai

# Deploy to Cloud Run
gcloud run deploy crowdpulse-ai \
  --image gcr.io/PROJECT/crowdpulse-ai \
  --platform managed \
  --allow-unauthenticated
```

---

## 📁 Project Structure

```
CrowdPulse/
├── app/
│   ├── main.py                 # FastAPI app factory
│   ├── config.py               # Pydantic Settings + venue graph
│   ├── config_data.py          # Ground-truth venue data
│   ├── models/                 # Pydantic request/response models
│   ├── api/                    # Route handlers (6 modules)
│   ├── crowd_engine/           # Simulator, predictor, wait times
│   ├── decision_engine/        # Scorer + Dijkstra router
│   ├── ai_engine/              # Gemini chatbot, explainer, advisor
│   ├── google_services/        # Firestore, BigQuery, Maps, Auth, Logging
│   └── middleware/             # Rate limiter
├── frontend/
│   ├── index.html              # SPA with full ARIA support
│   ├── css/style.css           # Premium design system
│   └── js/app.js               # Client-side logic
├── tests/                      # 302 tests across 15 test files
├── Dockerfile                  # Multi-stage, non-root
├── requirements.txt            # Pinned dependencies
├── .env.example                # Environment template
├── SECURITY.md                 # Security policy documentation
├── ACCESSIBILITY.md            # WCAG 2.1 AA compliance statement
├── GOOGLE_SERVICES.md          # Google Cloud integration guide
├── LICENSE                     # MIT License
└── README.md                   # This file
```

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.
