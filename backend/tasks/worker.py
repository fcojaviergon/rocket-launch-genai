"""
Configuración del worker de Celery para procesamiento asíncrono
"""
import os
import logging
from celery import Celery
from core.config import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('celery.worker')

# Crear app Celery
celery_app = Celery("worker")

# Configuración desde settings
celery_app.conf.broker_url = settings.REDIS_URL
celery_app.conf.result_backend = settings.REDIS_URL

# Configuraciones adicionales
celery_app.conf.update(
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutos
    accept_content=["json", "pickle"],
    task_serializer="json",
    result_serializer="json",
)

# Configurar importación automática de tareas
celery_app.autodiscover_tasks(['tasks'])

# Exportar para ser importado desde otros módulos
__all__ = ['celery_app'] 