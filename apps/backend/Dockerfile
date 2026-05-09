FROM python:3.12-slim

WORKDIR /app

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
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
