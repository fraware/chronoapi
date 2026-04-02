#!/bin/sh
set -e
WORKERS="${WORKER_COUNT:-4}"
exec gunicorn -k uvicorn.workers.UvicornWorker app.main:app \
  --bind 0.0.0.0:8000 \
  --workers "${WORKERS}"
