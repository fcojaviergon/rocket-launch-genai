"""
Modelo para el seguimiento de uso de tokens de OpenAI
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database.models.base import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.user import User

class TokenUsage(BaseModel):
    """Modelo para registrar el uso de tokens de OpenAI por usuario"""
    __tablename__ = "token_usage"
    
    # Relación con usuario
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", back_populates="token_usage")
    
    # Información de uso
    model = Column(String, nullable=False, index=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    
    # Tipo de operación (chat, embedding, etc.)
    operation_type = Column(String, nullable=False, index=True)
    
    # Metadatos adicionales (pipeline_id, document_id, etc.)
    token_usage_metadata = Column(JSONB, nullable=False, default={})
    
    # Timestamp
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
