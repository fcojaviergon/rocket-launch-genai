#!/bin/bash
set -e

# Wait for database to be ready
if [ "$POSTGRES_HOST" ]; then
  echo "Waiting for database..."
  while ! nc -z $POSTGRES_HOST 5432; do
    sleep 0.1
  done
  echo "Database started"
fi

# Ensure storage directory exists and has correct permissions for the app user
# This script runs as root (due to USER root before ENTRYPOINT in Dockerfile)
if [ -d "/app/storage/documents" ]; then
    echo "Ensuring ownership of /app/storage/documents for appuser..."
    chown -R appuser:appuser /app/storage/documents 
    echo "Ownership set for /app/storage/documents"
else
    echo "Warning: /app/storage/documents directory not found."
fi

# Run migrations (as root, often needed for Alembic)
if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "Running migrations..."
  alembic upgrade head
fi

# Execute the main command (passed as arguments: "$@") as the non-root user "appuser" using gosu
echo "Executing command as appuser: $@"
exec gosu appuser "$@" 