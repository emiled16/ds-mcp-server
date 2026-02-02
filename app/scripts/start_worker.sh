#!/bin/bash
# Start Celery worker for async job processing

set -e

cd "$(dirname "$0")/.."

echo "Starting Celery worker..."
celery -A src.workers.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --max-tasks-per-child=50

