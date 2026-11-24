#!/bin/sh
set -e

# 1. Bring the database schema up to date.
cd /app/backend
alembic upgrade head

# 2. Make sure the model weights are on the volume before accepting
#    searches (only slow on the very first start). A failure is not fatal:
#    the engine reports a detector fallback instead.
export MODELS_DIR="${MODELS_DIR:-/data/models}"
mkdir -p "$MODELS_DIR"
if [ "${SKIP_MODEL_DOWNLOAD:-false}" != "true" ]; then
  (cd /app/ml-engene && python -m tools.download_models) \
    || echo "WARNING: some models could not be downloaded; text search may be unavailable."
fi

# 3. Run from the models directory so any remaining Ultralytics assets
#    resolve there too.
cd "$MODELS_DIR"

# One worker: each process loads the ML models into memory and searches are
# serialised by the pipeline anyway. Scale with more containers if needed.
exec uvicorn main:app \
  --app-dir /app/backend \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers 1 \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" \
  --timeout-keep-alive 75
