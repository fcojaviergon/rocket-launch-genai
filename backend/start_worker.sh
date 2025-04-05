#!/bin/bash
# Script para iniciar un worker de Celery

# Configurar variables de entorno (se pueden sobreescribir con variables de entorno)
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_DB=${REDIS_DB:-0}
CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-4}
CELERY_POOL=${CELERY_POOL:-prefork}
CELERY_LOG_LEVEL=${CELERY_LOG_LEVEL:-info}

# Verificar si Redis está disponible
echo "Verificando conexión a Redis en $REDIS_HOST:$REDIS_PORT..."
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: No se puede conectar a Redis en $REDIS_HOST:$REDIS_PORT"
    echo "Asegúrate de que Redis esté en ejecución y sea accesible."
    exit 1
fi
echo "Conexión a Redis OK"

# Exportar variables para que Celery las use
export REDIS_URL="redis://$REDIS_HOST:$REDIS_PORT/$REDIS_DB"
export C_FORCE_ROOT=true  # Permite ejecutar Celery como root (solo para desarrollo)

echo "Iniciando worker de Celery con pool $CELERY_POOL y $CELERY_CONCURRENCY workers..."
echo "REDIS_URL: $REDIS_URL"

# Iniciar worker de Celery 
celery -A tasks.worker worker \
    --loglevel=$CELERY_LOG_LEVEL \
    --concurrency=$CELERY_CONCURRENCY \
    --pool=$CELERY_POOL \
    "$@"

echo "Worker detenido."