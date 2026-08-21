# ═══════════════════════════════════════════════════════════════════════════════
#  UNION BANK MANAGEMENT SYSTEM  —  Dockerfile
# ═══════════════════════════════════════════════════════════════════════════════
#  Multi-stage build:
#    - base:     shared Python environment with all dependencies
#    - api:      FastAPI REST API (port 8000)
#    - dev:      Development with hot-reload
#
#  Usage:
#    docker build --target api -t union-bank/api .
#    docker compose up        # runs api + Redis
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stage 0: Base Python image ──────────────────────────────────────────────
FROM python:3.11-slim AS base

LABEL org.opencontainers.image.title="Union Bank Management System"
LABEL org.opencontainers.image.description="FastAPI REST API for banking operations"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.licenses="MIT"

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    # Remove Debian's apt-managed python packages: python:3.11-slim ships
    # python3-msgpack 1.1.2 (GHSA-6v7p-g79w-8964, HIGH) and python3-setuptools
    # 70.3.0 (CVE-2025-47273) in /usr/lib/python3/dist-packages. The pip
    # install in the deps stage provides patched versions (msgpack 1.2.1,
    # setuptools 78.1.1+) in /usr/local, but Trivy scans every copy — so the
    # unpatched apt copies must be purged or the image scan fails.
    && apt-get purge -y --auto-remove python3-msgpack python3-setuptools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specs first (leverage Docker layer caching)
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    # Upgrade build-time/transitive packages with known HIGH CVEs
    # (setuptools CVE-2025-47273, wheel CVE-2026-24049, msgpack GHSA-6v7p-g79w-8964,
    #  jaraco.context CVE-2026-23949) — flagged by the CI trivy gate.
    pip install --no-cache-dir --upgrade \
        "setuptools>=78.1.1" \
        "wheel>=0.46.2" \
        "msgpack>=1.2.1" \
        "jaraco-context>=6.1.0"

# Copy application code (includes src/ directory)
COPY . .

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# Create data directory and fix ownership
RUN mkdir -p /app/data && chmod +x scripts/docker-entrypoint.sh \
    && chown -R app:app /app

USER app

# Expose port
EXPOSE 8000

# Default health check (uses liveness probe)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/healthz')" || exit 1


# ── Stage 1: FastAPI (production) ────────────────────────────────────────────
FROM base AS api

ENV ENTRYPOINT_TARGET=api
STOPSIGNAL SIGTERM
CMD ["sh", "-c", "exec scripts/docker-entrypoint.sh"]


# ── Stage 2: Development (hot-reload) ────────────────────────────────────────
FROM base AS dev

RUN pip install --no-cache-dir watchfiles

ENV ENTRYPOINT_TARGET=api
CMD ["sh", "-c", "exec scripts/docker-entrypoint.sh"]
