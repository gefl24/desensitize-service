#!/bin/sh
set -eu

/app/docker/cleanup-cache.sh || true
supercronic /app/docker/cleanup.cron &
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
