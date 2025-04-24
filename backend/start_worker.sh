#!/bin/bash
# Script para iniciar un worker de Celery

# Configurar variables de entorno (se pueden sobreescribir con variables de entorno)
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_DB=${REDIS_DB:-0}
CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-4}
CELERY_POOL=${CELERY_POOL:-prefork}  # Cambiado a 'solo' para soportar tareas asíncronas
CELERY_LOG_LEVEL=${CELERY_LOG_LEVEL:-info}

# Verificar si Redis está disponible
echo "Checking Redis connection at $REDIS_HOST:$REDIS_PORT..."
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Cannot connect to Redis at $REDIS_HOST:$REDIS_PORT"
    echo "Ensure Redis is running and accessible."
    exit 1
fi
echo "Connection to Redis OK"

# Export variables for Celery to use
export REDIS_URL="redis://$REDIS_HOST:$REDIS_PORT/$REDIS_DB"
export C_FORCE_ROOT=true  # Allow Celery to run as root (only for development)

# Add the parent directory (project root) to PYTHONPATH 
# This allows imports like 'from backend.core import ...' to work reliably
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "Starting Celery worker with pool $CELERY_POOL and $CELERY_CONCURRENCY workers..."
echo "REDIS_URL: $REDIS_URL"
echo "PYTHONPATH set to: $PYTHONPATH"

# Start Celery worker
# Ensure the Celery app is specified correctly relative to the project root
# Assuming your tasks.worker is in backend/tasks/worker.py
celery -A backend.tasks.worker worker \
    --loglevel=$CELERY_LOG_LEVEL \
    --concurrency=$CELERY_CONCURRENCY \
    --pool=$CELERY_POOL \
    "$@"

echo "Worker stopped."