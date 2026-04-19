# Security Policy — CrowdPulse AI

## Overview

CrowdPulse AI implements a defence-in-depth security model across all layers of the application stack. This document describes every security control, its rationale, and how it is tested.

---

## 1. HTTP Security Headers

Every response includes the following headers, enforced by middleware in `app/main.py`:

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline' ...` | Prevents XSS by restricting resource origins |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing attacks |
| `X-Frame-Options` | `DENY` | Prevents clickjacking via iframe embedding |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limits referrer leakage to third parties |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(self), payment=()` | Restricts browser API access |
| `X-Permitted-Cross-Domain-Policies` | `none` | Prevents Flash/PDF cross-domain reads |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Enforces HTTPS (production only) |

**Tests:** `tests/test_security.py::TestSecurityHeaders`

---

## 2. CORS Configuration

- **Debug mode:** Allows all origins (`*`) for local development convenience.
- **Production mode:** Requires explicit whitelist via `ALLOWED_ORIGINS` environment variable.
- **Allowed methods:** `GET`, `POST`, `OPTIONS` only.
- **Allowed headers:** `Authorization`, `Content-Type` only.
- **Credentials:** Supported for Firebase Auth token flows.

**Tests:** `tests/test_security.py::TestCorsConfiguration`

---

## 3. Rate Limiting

Sliding-window, per-IP rate limiting implemented in `app/middleware/rate_limiter.py`:

| Endpoint Group | Threshold | Window |
|---------------|-----------|--------|
| Navigation (`/navigate/*`) | 10 requests | 60 seconds |
| Chat (`/assistant/*`) | 20 requests | 60 seconds |
| Analytics (`/analytics/*`) | 15 requests | 60 seconds |
| Crowd (`/crowd/*`) | 30 requests | 60 seconds |

- Uses `X-Forwarded-For` header for Cloud Run proxy awareness.
- Returns `HTTP 429` with `Retry-After` header when exceeded.
- Backed by `collections.deque` for O(1) amortized operations.

**Tests:** `tests/test_security.py::TestNavigationRateLimit`, `TestChatRateLimit`

---

## 4. Input Validation

All request bodies use Pydantic models with strict constraints:

| Field | Constraint | Rationale |
|-------|-----------|-----------|
| `user_id` | 1–64 chars | Prevents empty or oversized identifiers |
| `current_zone` | 1–32 chars | Bounds zone ID input |
| `destination` | 1–32 chars | Bounds zone ID input |
| `message` (chat) | 1–500 chars, whitespace-stripped | Prevents empty/oversized prompts |
| `constraints` | Max 5 items | Bounds array size |
| `user_note` | Max 256 chars | Bounds free-text input |

**Tests:** `tests/test_security.py::TestChatInputValidation`, `TestNavigationInputValidation`

---

## 5. Authentication

Firebase Auth token verification via `app/google_services/firebase_auth.py`:

- **Production:** Verifies Firebase ID tokens using `firebase-admin` SDK.
- **Development:** Accepts `mock-*` tokens for testing without Firebase project.
- **Header format:** `Authorization: Bearer <token>`

**Tests:** `tests/test_auth.py`

---

## 6. Container Security

The `Dockerfile` implements:

- **Multi-stage build:** Separates build dependencies from runtime.
- **Non-root execution:** Application runs as `appuser` (UID 10001).
- **No shell access:** Uses `CMD` with exec form, no `/bin/sh`.
- **Minimal image:** Based on `python:3.11-slim` with only runtime dependencies.
- **Health checks:** Built-in Docker HEALTHCHECK against `/health`.

---

## 7. Secret Management

- No secrets are hardcoded. All sensitive values are loaded from environment variables via Pydantic Settings.
- `.env` files are excluded from version control via `.gitignore`.
- `.env.example` documents all required variables with safe placeholder values.

---

## 8. AI Safety

- Gemini AI is **never used for routing decisions** — only for explanation and phrasing.
- The chatbot has a **grounding pipeline**: intent is classified deterministically, facts are resolved from structured data, and Gemini only phrases the pre-resolved answer.
- Gemini failures are caught and replaced with deterministic fallback text.
- System instructions explicitly prohibit speculation about safety, medical, or emergency guidance.

---

## 9. SQL Injection Prevention

- All BigQuery queries use **parameterized queries** with `@parameter` syntax.
- No f-string interpolation is used for user-supplied values.
- The `top_n` parameter is clamped to `[1, 20]` and cast to `int()` before use.

**Tests:** `tests/test_google_services.py::TestBigQueryMock`

---

## Reporting Vulnerabilities

If you discover a security issue, please email security@crowdpulse.dev with a description. We will acknowledge within 48 hours.
