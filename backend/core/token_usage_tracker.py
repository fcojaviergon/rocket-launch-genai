"""
Sistema de seguimiento de uso de tokens de OpenAI por usuario
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models.user import User
from core.token_counter import TokenCounter

logger = logging.getLogger(__name__)

class TokenUsageTracker:
    """
    Clase para rastrear el uso de tokens de OpenAI por usuario
    """
    
    def __init__(self, db: AsyncSession = None):
        """Inicializar con una sesión de base de datos asíncrona"""
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
    

    
    async def check_user_quota(self, user_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """
        Verificar si un usuario ha excedido su cuota de tokens
        
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
            
            # Obtener plan del usuario
            plan = user.plan or "free"
            
            # Obtener límites del plan
            quota_limits = {
                "free": 100000,       # 100K tokens/mes
                "basic": 500000,      # 500K tokens/mes
                "premium": 2000000,    # 2M tokens/mes
                "enterprise": 10000000 # 10M tokens/mes
            }
            
            # Obtener límite para el plan del usuario
            quota_limit = quota_limits.get(plan.lower(), 100000)  # Default a free si no se reconoce el plan
            
            # Calcular uso de tokens en el mes actual
            from database.models.token_usage import TokenUsage
            
            # Obtener el primer día del mes actual
            today = datetime.utcnow()
            first_day = datetime(today.year, today.month, 1)
            
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
    
    async def estimate_cost(
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
