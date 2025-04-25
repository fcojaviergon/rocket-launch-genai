"""
Sistema de seguimiento de uso de tokens de OpenAI por usuario
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from database.models.user import User
from database.models.token_usage import TokenUsage
from core.token_counter import TokenCounter

logger = logging.getLogger(__name__)

class TokenUsageTracker:
    """
    Clase para rastrear el uso de tokens de OpenAI por usuario
    """
    
    def __init__(self, db = None):
        """Inicializar con una sesión de base de datos (asíncrona o síncrona)"""
        self.db = db
    
    async def record_usage(
        self, 
        user_id: Union[str, uuid.UUID], 
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        operation_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Registrar uso de tokens para un usuario
        
        Args:
            user_id: ID del usuario
            model: Modelo de OpenAI usado
            prompt_tokens: Tokens usados en el prompt
            completion_tokens: Tokens usados en la respuesta
            operation_type: Tipo de operación (chat, embedding, etc.)
            metadata: Metadatos adicionales
            
        Returns:
            Dict con información del registro
        """
        if not self.db:
            logger.warning(f"No hay sesión de base de datos disponible para registrar uso de tokens de usuario {user_id}")
            return {
                "recorded": False,
                "error": "No database session available"
            }
        
        try:
            # Importar modelo aquí para evitar importaciones circulares
            from database.models.token_usage import TokenUsage
            
            # Convertir a UUID si es string
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            
            # Crear registro de uso
            usage_record = TokenUsage(
                user_id=user_id,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                operation_type=operation_type,
                metadata=metadata or {},
                timestamp=datetime.utcnow()
            )
            
            # Guardar en base de datos de forma asíncrona
            self.db.add(usage_record)
            await self.db.commit()
            await self.db.refresh(usage_record)
            
            logger.info(f"Registrado uso de {prompt_tokens + completion_tokens} tokens para usuario {user_id}")
            
            return {
                "recorded": True,
                "usage_id": str(usage_record.id),
                "user_id": str(user_id),
                "total_tokens": prompt_tokens + completion_tokens
            }
            
        except Exception as e:
            logger.error(f"Error al registrar uso de tokens para usuario {user_id}: {e}", exc_info=True)
            # Intentar hacer rollback
            try:
                await self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error adicional al hacer rollback: {rollback_error}")
            
            return {
                "recorded": False,
                "error": str(e)
            }
    

    
    def record_usage_sync(
        self, 
        user_id: Union[str, uuid.UUID], 
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        operation_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Registrar uso de tokens para un usuario de forma síncrona
        
        Args:
            user_id: ID del usuario
            model: Modelo de OpenAI usado
            prompt_tokens: Tokens usados en el prompt
            completion_tokens: Tokens usados en la respuesta
            operation_type: Tipo de operación (chat, embedding, etc.)
            metadata: Metadatos adicionales
            
        Returns:
            Dict con información del registro
        """
        if not self.db:
            logger.warning(f"No hay sesión de base de datos disponible para registrar uso de tokens de usuario {user_id}")
            return {
                "recorded": False,
                "error": "No database session available"
            }
        
        try:
            # Convertir a UUID si es string
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            
            # Crear registro de uso
            usage_record = TokenUsage(
                user_id=user_id,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                operation_type=operation_type,
                metadata=metadata or {},
                timestamp=datetime.utcnow()
            )
            
            # Guardar en base de datos de forma síncrona
            self.db.add(usage_record)
            self.db.commit()
            self.db.refresh(usage_record)
            
            logger.info(f"Registrado uso de {prompt_tokens + completion_tokens} tokens para usuario {user_id} (sync)")
            
            return {
                "recorded": True,
                "usage_id": str(usage_record.id),
                "user_id": str(user_id),
                "total_tokens": prompt_tokens + completion_tokens
            }
            
        except Exception as e:
            logger.error(f"Error al registrar uso de tokens para usuario {user_id} (sync): {e}", exc_info=True)
            # Intentar hacer rollback
            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error adicional al hacer rollback: {rollback_error}")
            
            return {
                "recorded": False,
                "error": str(e)
            }
    
    def check_user_quota_sync(self, user_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """
        Verificar si un usuario ha excedido su cuota de tokens de forma síncrona
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con información de la cuota
        """
        if not self.db:
            logger.warning(f"No hay sesión de base de datos disponible para verificar cuota de usuario {user_id}")
            return {
                "has_quota": True,  # Por defecto permitir si no podemos verificar
                "error": "No database session available"
            }
        
        try:
            # Convertir a UUID si es string
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            
            # Obtener información del usuario
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user:
                logger.warning(f"Usuario {user_id} no encontrado en la base de datos")
                return {
                    "has_quota": True,  # Por defecto permitir si no encontramos al usuario
                    "error": "User not found"
                }
            
            # Obtener límite de cuota del usuario (o usar valor por defecto)
            try:
                quota_limit = getattr(user, "token_quota", 1000000) or 1000000  # 1M tokens por defecto
            except AttributeError:
                quota_limit = 1000000  # 1M tokens por defecto
                logger.warning(f"Usuario {user_id} no tiene atributo 'token_quota', usando límite por defecto")
            
            # Calcular primer día del mes actual para contar tokens desde esa fecha
            today = datetime.utcnow()
            first_day = datetime(today.year, today.month, 1)
            
            # Contar tokens usados en el mes actual
            used_tokens = self.db.query(func.sum(TokenUsage.total_tokens))\
                .filter(
                    TokenUsage.user_id == user_id,
                    TokenUsage.timestamp >= first_day
                ).scalar() or 0
            
            # Calcular tokens restantes y porcentaje de uso
            remaining_tokens = max(0, quota_limit - used_tokens)
            usage_percent = (used_tokens / quota_limit) * 100 if quota_limit > 0 else 100
            
            # Determinar si el usuario aún tiene cuota disponible
            has_quota = used_tokens < quota_limit
            
            # Preparar información de cuota
            quota_info = {
                "has_quota": has_quota,
                "used_tokens": used_tokens,
                "quota_limit": quota_limit,
                "remaining_tokens": remaining_tokens,
                "usage_percent": usage_percent
            }
            
            # Registrar en log si el usuario está cerca del límite o lo ha excedido
            if usage_percent >= 90:
                logger.warning(f"Usuario {user_id} ha usado {usage_percent:.1f}% de su cuota de tokens ({used_tokens}/{quota_limit}) (sync)")
            
            return quota_info
            
        except Exception as e:
            logger.error(f"Error al verificar cuota de usuario {user_id} (sync): {e}", exc_info=True)
            # Intentar hacer rollback si es necesario
            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error adicional al hacer rollback: {rollback_error}")
            
            return {
                "has_quota": True,  # Por defecto permitir si hay error
                "error": str(e)
            }
    
    async def check_user_quota(self, user_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """
        Verificar si un usuario ha excedido su cuota de tokens de forma asíncrona
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con información de la cuota
        """
        if not self.db:
            logger.warning(f"No hay sesión de base de datos disponible para verificar cuota de usuario {user_id}")
            return {
                "has_quota": True,  # Por defecto permitir si no hay DB
                "error": "No database session available"
            }
        
        try:
            # Convertir a UUID si es string
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            
            # Verificar si self.db es una sesión o un context manager
            from sqlalchemy.ext.asyncio import AsyncSession
            from contextlib import AbstractAsyncContextManager
            
            # Si self.db no es una sesión directamente, podría ser un context manager
            if not isinstance(self.db, AsyncSession):
                logger.info(f"self.db no es una AsyncSession, asumiendo que es un context manager")
                
                # Verificar si es un context manager asíncrono
                if isinstance(self.db, AbstractAsyncContextManager):
                    # Usar el context manager correctamente
                    async with self.db as session:
                        # Obtener usuario y su plan
                        stmt = select(User).where(User.id == user_id)
                        result = await session.execute(stmt)
                        user = result.scalar_one_or_none()
                        
                        if not user:
                            logger.warning(f"Usuario {user_id} no encontrado para verificar cuota")
                            return {
                                "has_quota": False,
                                "error": "User not found"
                            }
                        
                        # Obtener plan del usuario (con manejo de atributos faltantes)
                        try:
                            plan = getattr(user, "plan", "free") or "free"
                        except AttributeError:
                            plan = "free"
                            logger.info(f"Usuario {user_id} no tiene atributo 'plan', usando plan 'free' por defecto")
                        
                        # Devolver respuesta básica con el plan
                        return {
                            "has_quota": True,
                            "plan": plan,
                            "message": "Quota check simplified due to context manager session"
                        }
                else:
                    # No es un context manager asíncrono, devolver respuesta por defecto
                    return {
                        "has_quota": True,  # Por defecto permitir
                        "error": "Cannot check quota with current session type"
                    }
            
            # Obtener usuario y su plan (método asíncrono)
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"Usuario {user_id} no encontrado para verificar cuota")
                return {
                    "has_quota": False,
                    "error": "User not found"
                }
            
            # Obtener plan del usuario (con manejo de atributos faltantes)
            try:
                plan = getattr(user, "plan", "free") or "free"
            except AttributeError:
                # Si el modelo de usuario no tiene un atributo plan, usar "free" por defecto
                plan = "free"
                logger.info(f"Usuario {user_id} no tiene atributo 'plan', usando plan 'free' por defecto")
            
            # Verificar si el usuario tiene un límite de tokens personalizado
            try:
                token_quota = getattr(user, "token_quota", None)
                if token_quota:
                    quota_limit = token_quota
                    logger.info(f"Usuario {user_id} tiene límite personalizado de {quota_limit} tokens")
                else:
                    # Obtener límites del plan
                    quota_limits = {
                        "free": 100000,       # 100K tokens/mes
                        "basic": 500000,      # 500K tokens/mes
                        "premium": 2000000,    # 2M tokens/mes
                        "enterprise": 10000000 # 10M tokens/mes
                    }
                    
                    # Obtener límite para el plan del usuario
                    quota_limit = quota_limits.get(plan.lower(), 100000)  # Default a free si no se reconoce el plan
            except AttributeError:
                # Si hay error al acceder a token_quota, usar límite basado en plan
                quota_limits = {
                    "free": 100000,       # 100K tokens/mes
                    "basic": 500000,      # 500K tokens/mes
                    "premium": 2000000,    # 2M tokens/mes
                    "enterprise": 10000000 # 10M tokens/mes
                }
                
                # Obtener límite para el plan del usuario
                quota_limit = quota_limits.get(plan.lower(), 100000)  # Default a free si no se reconoce el plan
                logger.warning(f"Error al acceder a token_quota para usuario {user_id}, usando límite de plan: {quota_limit}")
            
            # Calcular uso de tokens en el mes actual
            from database.models.token_usage import TokenUsage
            from sqlalchemy import func
            import calendar
            from datetime import datetime, timedelta
            
            # Obtener primer día del mes actual
            now = datetime.utcnow()
            first_day = datetime(now.year, now.month, 1)
            
            # Consultar uso total de tokens en el mes actual
            stmt = select(func.sum(TokenUsage.total_tokens)).where(
                TokenUsage.user_id == user_id,
                TokenUsage.timestamp >= first_day
            )
            result = await self.db.execute(stmt)
            used_tokens = result.scalar() or 0
            
            # Calcular tokens restantes y porcentaje de uso
            remaining_tokens = max(0, quota_limit - used_tokens)
            usage_percent = (used_tokens / quota_limit) * 100 if quota_limit > 0 else 100
            
            # Determinar si el usuario aún tiene cuota disponible
            has_quota = used_tokens < quota_limit
            
            # Preparar información de cuota
            quota_info = {
                "has_quota": has_quota,
                "used_tokens": used_tokens,
                "quota_limit": quota_limit,
                "remaining_tokens": remaining_tokens,
                "usage_percent": usage_percent
            }
            
            # Registrar en log si el usuario está cerca del límite o lo ha excedido
            if usage_percent >= 90:
                logger.warning(f"Usuario {user_id} ha usado {usage_percent:.1f}% de su cuota de tokens ({used_tokens}/{quota_limit})")
            
            return quota_info
            
        except Exception as e:
            logger.error(f"Error al verificar cuota de usuario {user_id}: {e}", exc_info=True)
            # Intentar hacer rollback si es necesario
            try:
                await self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error adicional al hacer rollback: {rollback_error}")
            
            return {
                "has_quota": True,  # Por defecto permitir si hay error
                "error": str(e)
            }
    
    def estimate_cost(
        self, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int
    ) -> Dict[str, float]:
        """
        Estimar costo en USD del uso de tokens
        
        Args:
            model: Modelo de OpenAI usado
            prompt_tokens: Tokens usados en el prompt
            completion_tokens: Tokens usados en la respuesta
            
        Returns:
            Dict con información del costo
        """
        # Precios por 1000 tokens según la documentación de OpenAI (abril 2023)
        # Estos precios pueden cambiar, mantener actualizado
        pricing = {
            # GPT-4 Turbo
            "gpt-4-turbo-preview": {"prompt": 0.01, "completion": 0.03},
            "gpt-4-0125-preview": {"prompt": 0.01, "completion": 0.03},
            "gpt-4-1106-preview": {"prompt": 0.01, "completion": 0.03},
            
            # GPT-4
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-0613": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-32k": {"prompt": 0.06, "completion": 0.12},
            "gpt-4-32k-0613": {"prompt": 0.06, "completion": 0.12},
            
            # GPT-3.5 Turbo
            "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
            "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004},
            "gpt-3.5-turbo-0613": {"prompt": 0.0015, "completion": 0.002},
            "gpt-3.5-turbo-16k-0613": {"prompt": 0.003, "completion": 0.004},
            
            # Embedding models
            "text-embedding-ada-002": {"prompt": 0.0001, "completion": 0},
            "text-embedding-3-small": {"prompt": 0.00002, "completion": 0},
            "text-embedding-3-large": {"prompt": 0.00013, "completion": 0},
        }
        
        # Usar precios por defecto si el modelo no está en la lista
        model_pricing = pricing.get(model, {"prompt": 0.002, "completion": 0.002})
        
        # Calcular costo
        prompt_cost = (prompt_tokens / 1000) * model_pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * model_pricing["completion"]
        total_cost = prompt_cost + completion_cost
        
        return {
            "prompt_cost": prompt_cost,
            "completion_cost": completion_cost,
            "total_cost": total_cost,
            "currency": "USD"
        }
