"""
Sistema unificado de eventos para la aplicación
Combina eventos internos (bus de eventos) y notificaciones en tiempo real (Redis)
"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List, Union
from redis import Redis
from redis import asyncio as redis_asyncio
from core.config import settings

logger = logging.getLogger(__name__)

class UnifiedEventManager:
    """
    Gestor unificado de eventos que combina:
    1. Bus de eventos interno para comunicación entre componentes
    2. Sistema de notificaciones en tiempo real con Redis
    """
    
    def __init__(self):
        """Inicializar el gestor de eventos"""
        # Bus de eventos interno
        self.handlers = {}
        
        # Conexión a Redis para eventos en tiempo real (síncrona)
        try:
            self.redis = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=5
            )
            self.pubsub = self.redis.pubsub()
            self.redis_available = True
            
            # Conexión asíncrona a Redis (para uso con código asíncrono)
            self.async_redis = None
            # No inicializamos la conexión asíncrona aquí para evitar bloqueos
            # Se inicializará bajo demanda en get_async_redis()
        except Exception as e:
            logger.warning(f"No se pudo conectar a Redis: {e}. Las notificaciones en tiempo real estarán deshabilitadas.")
            self.redis_available = False
            
    async def get_async_redis(self):
        """Obtener conexión asíncrona a Redis (inicializada bajo demanda)"""
        if not self.redis_available:
            return None
            
        if self.async_redis is None:
            try:
                self.async_redis = await redis_asyncio.from_url(
                    settings.REDIS_URL,
                    decode_responses=True
                )
            except Exception as e:
                logger.error(f"Error al crear conexión asíncrona a Redis: {e}")
                return None
                
        return self.async_redis
    
    # ===== Métodos del bus de eventos interno =====
    
    async def publish(self, event):
        """
        Publicar un evento en el bus interno
        
        Args:
            event: Objeto de evento con atributo event_type
        """
        event_type = event.event_type
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                await handler(event)
                
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Suscribir un manejador a un tipo de evento interno
        
        Args:
            event_type: Tipo de evento
            handler: Función manejadora
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        
    def register_handler(self, event_type: str) -> Callable:
        """
        Decorador para registrar un manejador de eventos
        
        Args:
            event_type: Tipo de evento
            
        Returns:
            Callable: Decorador
        """
        def decorator(handler):
            self.subscribe(event_type, handler)
            return handler
        return decorator
    
    # ===== Métodos para notificaciones en tiempo real con Redis =====
    
    def publish_realtime(self, channel: str, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Publicar un evento en tiempo real usando Redis (versión síncrona)
        
        Args:
            channel: Canal donde publicar (ej: 'pipeline:{id}')
            event_type: Tipo de evento (ej: 'processing_started')
            data: Datos del evento
            
        Returns:
            bool: True si se publicó correctamente
        """
        if not self.redis_available:
            logger.warning("Redis no está disponible. No se pudo publicar evento en tiempo real.")
            return False
            
        try:
            payload = {
                "event_type": event_type,
                "data": data
            }
            
            self.redis.publish(channel, json.dumps(payload))
            logger.debug(f"Evento publicado en canal {channel}: {event_type}")
            return True
        except Exception as e:
            logger.error(f"Error al publicar evento en tiempo real: {e}")
            return False
            
    async def publish_realtime_async(self, channel: str, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Publicar un evento en tiempo real usando Redis (versión asíncrona)
        
        Args:
            channel: Canal donde publicar (ej: 'pipeline:{id}')
            event_type: Tipo de evento (ej: 'processing_started')
            data: Datos del evento
            
        Returns:
            bool: True si se publicó correctamente
        """
        if not self.redis_available:
            logger.warning("Redis no está disponible. No se pudo publicar evento en tiempo real.")
            return False
            
        try:
            redis = await self.get_async_redis()
            if not redis:
                logger.warning("No se pudo obtener conexión asíncrona a Redis")
                # Fallback a la versión síncrona
                return self.publish_realtime(channel, event_type, data)
                
            payload = {
                "event_type": event_type,
                "data": data
            }
            
            await redis.publish(channel, json.dumps(payload))
            logger.debug(f"Evento publicado de forma asíncrona en canal {channel}: {event_type}")
            return True
        except Exception as e:
            logger.error(f"Error al publicar evento en tiempo real de forma asíncrona: {e}")
            # Intentar fallback a la versión síncrona
            try:
                return self.publish_realtime(channel, event_type, data)
            except Exception as inner_e:
                logger.error(f"Error en fallback síncrono: {inner_e}")
                return False
            
    def subscribe_realtime(self, channels: Union[str, List[str]]) -> None:
        """
        Suscribirse a uno o más canales de Redis (versión síncrona)
        
        Args:
            channels: Canal o lista de canales a suscribirse
        """
        if not self.redis_available:
            logger.warning("Redis no está disponible. No se pudo suscribir a canales.")
            return
            
        if isinstance(channels, str):
            channels = [channels]
            
        self.pubsub.subscribe(*channels)
        
    async def subscribe_realtime_async(self, channels: Union[str, List[str]]) -> None:
        """
        Suscribirse a uno o más canales de Redis (versión asíncrona)
        
        Args:
            channels: Canal o lista de canales a suscribirse
        """
        if not self.redis_available:
            logger.warning("Redis no está disponible. No se pudo suscribir a canales.")
            return
            
        redis = await self.get_async_redis()
        if not redis:
            logger.warning("No se pudo obtener conexión asíncrona a Redis")
            # Fallback a la versión síncrona
            self.subscribe_realtime(channels)
            return
            
        if isinstance(channels, str):
            channels = [channels]
            
        # Crear pubsub asíncrono
        pubsub = redis.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub
        
    def listen_realtime(self, callback: Callable) -> None:
        """
        Escuchar eventos en canales suscritos de Redis (versión síncrona)
        
        Args:
            callback: Función a llamar cuando se recibe un evento
        """
        if not self.redis_available:
            logger.warning("Redis no está disponible. No se puede escuchar eventos.")
            return
            
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    payload = json.loads(message['data'])
                    callback(message['channel'], payload)
                except Exception as e:
                    logger.error(f"Error al procesar mensaje de Redis: {e}")
                    
    async def listen_realtime_async(self, pubsub, callback: Callable) -> None:
        """
        Escuchar eventos en canales suscritos de Redis (versión asíncrona)
        
        Args:
            pubsub: Objeto pubsub asíncrono (de subscribe_realtime_async)
            callback: Función asíncrona a llamar cuando se recibe un evento
        """
        if not self.redis_available:
            logger.warning("Redis no está disponible. No se puede escuchar eventos.")
            return
            
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    payload = json.loads(message['data'])
                    await callback(message['channel'], payload)
                except Exception as e:
                    logger.error(f"Error al procesar mensaje de Redis de forma asíncrona: {e}")

# Singleton para acceder al gestor de eventos
_event_manager = None

def get_event_manager() -> UnifiedEventManager:
    """
    Obtener la instancia del gestor de eventos unificado
    
    Returns:
        UnifiedEventManager: Instancia del gestor de eventos
    """
    global _event_manager
    if _event_manager is None:
        _event_manager = UnifiedEventManager()
    return _event_manager

# Alias para compatibilidad con código existente
event_bus = get_event_manager()
