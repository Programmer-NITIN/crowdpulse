# ─────────────────────────────────────────────────────────────────────────────
# CrowdPulse AI — Multi-stage Docker Build
#
# Stage 1: Install dependencies in an intermediate layer for cache efficiency.
# Stage 2: Copy only the runtime artefacts into a slim final image.
# Runs as a non-root user for production security.
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="CrowdPulse AI Team"
LABEL description="Intelligent Crowd Navigation Assistant for Large Venues"

# Security: run as non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY frontend/ ./frontend/

# Set ownership and permissions
RUN chown -R appuser:appuser /app && chmod -R 755 /app

USER appuser

# Cloud Run injects PORT; default to 8080 for local testing
ENV PORT=8080

EXPOSE ${PORT}

# Health check for container orchestrators
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1
