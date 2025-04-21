"""
Estrategias de reintento avanzadas para tareas de Celery
"""
import logging
import random
from functools import wraps
from typing import Dict, Any, Callable, Optional, Union, List, Tuple, Type

from celery import Task
from celery.exceptions import Retry

logger = logging.getLogger('tasks.retry')

class RetryPolicy:
    """
    Define la política de reintentos para una tarea
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        countdown_base: int = 5,  # Segundos
        exponential_backoff: bool = True,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.1,
        retry_errors: Optional[List[Union[Type[Exception], Tuple[Type[Exception], ...]]]] = None,
        retry_for_unexpected: bool = True
    ):
        """
        Inicializa una política de reintentos
        
        Args:
            max_retries: Número máximo de reintentos
            countdown_base: Tiempo base de espera para reintentos (segundos)
            exponential_backoff: Si se usa backoff exponencial
            backoff_factor: Factor para cálculo del backoff exponencial
            jitter: Si se agrega variación aleatoria al tiempo de espera
            jitter_factor: Factor para el cálculo de jitter (0.0-1.0)
            retry_errors: Lista de excepciones para reintentar
            retry_for_unexpected: Si se reintenta para excepciones no especificadas
        """
        self.max_retries = max_retries
        self.countdown_base = countdown_base
        self.exponential_backoff = exponential_backoff
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        
        # Si no se especifican errores, usar una lista predeterminada
        if retry_errors is None:
            retry_errors = [
                # Errores de red/conexión
                ConnectionError, TimeoutError,
                # Añadir más tipos de errores según necesidades
            ]
        self.retry_errors = retry_errors
        self.retry_for_unexpected = retry_for_unexpected
        
    def calculate_countdown(self, retries: int) -> int:
        """
        Calcula el tiempo de espera para el siguiente reintento
        
        Args:
            retries: Número actual de reintentos
            
        Returns:
            Tiempo de espera en segundos
        """
        if self.exponential_backoff:
            countdown = self.countdown_base * (self.backoff_factor ** retries)
        else:
            countdown = self.countdown_base
            
        if self.jitter:
            # Añadir variación aleatoria (jitter) para evitar thundering herd
            jitter_range = countdown * self.jitter_factor
            countdown += random.uniform(-jitter_range, jitter_range)
            
        return max(1, int(countdown))  # Mínimo 1 segundo
        
    def should_retry(self, exception: Exception) -> bool:
        """
        Determina si se debe reintentar basado en la excepción
        
        Args:
            exception: La excepción que se produjo
            
        Returns:
            True si se debe reintentar, False en caso contrario
        """
        # Verificar si es un tipo de excepción específicamente marcado para reintento
        for error_type in self.retry_errors:
            if isinstance(exception, error_type):
                return True
                
        # Para errores no especificados, usar la política general
        return self.retry_for_unexpected

def apply_retry_policy(policy: Optional[RetryPolicy] = None, **kwargs):
    """
    Decorador para aplicar una política de reintentos a una tarea Celery
    
    Args:
        policy: Política de reintentos a aplicar
        **kwargs: Argumentos alternativos para crear una política
        
    Returns:
        Función decoradora
    """
    # Si no se proporciona una política, crear una con los argumentos
    if policy is None:
        policy = RetryPolicy(**kwargs)
        
    def decorator(task_func):
        @wraps(task_func)
        def wrapper(self, *args, **kwargs):
            # En tareas con bind=True, 'self' es la instancia de Task
            try:
                return task_func(self, *args, **kwargs)
            except Exception as exc:
                if not policy.should_retry(exc):
                    logger.warning(f"No se reintentará la tarea {self.name}: {exc}")
                    raise
                
                # Verificar si aún podemos reintentar
                if self.request.retries >= policy.max_retries:
                    logger.error(f"Tarea {self.name} falló después de {self.request.retries} reintentos: {exc}")
                    raise
                
                # Calcular tiempo de espera
                countdown = policy.calculate_countdown(self.request.retries)
                
                logger.info(f"Reintentando tarea {self.name} ({self.request.retries + 1}/{policy.max_retries}) "
                           f"después de {countdown}s debido a: {exc}")
                
                # Lanzar la excepción Retry que Celery capturará
                raise self.retry(exc=exc, countdown=countdown, max_retries=policy.max_retries)
        
        return wrapper
    
    return decorator

# Predefinir algunas políticas comunes
DEFAULT_RETRY_POLICY = RetryPolicy(
    max_retries=3,
    countdown_base=5,
    exponential_backoff=True,
    jitter=True
)

AGGRESSIVE_RETRY_POLICY = RetryPolicy(
    max_retries=5,
    countdown_base=2,
    exponential_backoff=True,
    jitter=True,
    retry_for_unexpected=True
)

GENTLE_RETRY_POLICY = RetryPolicy(
    max_retries=3,
    countdown_base=30,
    exponential_backoff=True,
    jitter=True,
    retry_for_unexpected=False
)