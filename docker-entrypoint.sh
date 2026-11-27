#!/bin/sh

set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting Stored Procedure Migration service..."
if [ $# -gt 0 ]; then
    exec "$@"
else
    exec uvicorn src.main:app --host 0.0.0.0 --port 8000
fi
