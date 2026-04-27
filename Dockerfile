# ── vCenter AI Admin ─ FastAPI service ──────────────────────────────
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies: gcc, curl (for pyVmomi build + govc binary)
# govc: map Debian arch -> govmomi release asset (amd64=x86_64, arm64=arm64)
ARG GOVOMI_VERSION=v0.38.0
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ca-certificates \
    curl \
    tar \
    && set -eux; \
    arch=$(dpkg --print-architecture); \
    case "$arch" in \
      amd64) t=x86_64 ;; \
      arm64) t=arm64 ;; \
      *) echo "unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/vmware/govmomi/releases/download/${GOVOMI_VERSION}/govc_Linux_${t}.tar.gz" \
      | tar -xz -C /usr/local/bin govc; \
    chmod +x /usr/local/bin/govc; \
    /usr/local/bin/govc version; \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Expose FastAPI port (internal only — nginx proxies to this)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status')" || exit 1

# Start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
