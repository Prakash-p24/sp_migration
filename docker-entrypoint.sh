#!/bin/sh

set -e

echo "Starting Stored Procedure Migration service..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000