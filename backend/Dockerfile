# syntax=docker/dockerfile:1
# Build from the repository root (the image needs both backend/ and ml-engene/):
#   docker build -f backend/Dockerfile -t mlft-backend .

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# OpenCV runtime libraries + curl for the health check.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# CPU PyTorch by default; pass --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu128 for CUDA.
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
COPY backend/requirements.txt ./requirements.txt
RUN pip install --extra-index-url "$TORCH_INDEX" -r requirements.txt

COPY ml-engene /app/ml-engene
COPY backend /app/backend
RUN chmod +x /app/backend/docker-entrypoint.sh \
 && useradd --system --uid 10001 --home /app app \
 && mkdir -p /data/storage /data/models \
 && chown -R app:app /data

ENV APP_ENV=production \
    STORAGE_DIR=/data/storage \
    ML_ENGINE_DIR=/app/ml-engene \
    MODELS_DIR=/data/models \
    HF_HOME=/data/models/huggingface \
    YOLO_CONFIG_DIR=/data/models/ultralytics

USER app
EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
