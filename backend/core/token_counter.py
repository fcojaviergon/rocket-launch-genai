"""
Utilidad para contar tokens en textos para modelos de OpenAI
"""
import tiktoken
import logging
from typing import List, Dict, Any, Union, Optional

logger = logging.getLogger(__name__)

class TokenCounter:
    """
    Clase para contar tokens en textos para diferentes modelos de OpenAI
    """
    
    # Mapeo de modelos a codificadores
    MODEL_TO_ENCODING = {

        # GPT-4
        "gpt-4": "cl100k_base",
        "gpt-4-mini": "cl100k_base",

        # Embedding models
        "text-embedding-ada-002": "cl100k_base",
        "text-embedding-3-small": "cl100k_base",
        "text-embedding-3-large": "cl100k_base",
    }
    
    # Límites de contexto por modelo (tokens)
    MODEL_CONTEXT_LIMITS = {
        # GPT-4
        "gpt-4": 128000,
        "gpt-4-mini": 128000, 
    }
    
    @classmethod
    def get_encoder(cls, model: str):
        """
        Obtener el codificador para un modelo específico
        
        Args:
            model: Nombre del modelo
            
        Returns:
            Codificador de tiktoken
        """
        encoding_name = cls.MODEL_TO_ENCODING.get(model, "cl100k_base")
        try:
            return tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.error(f"Error al obtener codificador para modelo {model}: {e}")
            # Usar cl100k_base como fallback
            return tiktoken.get_encoding("cl100k_base")
    
    @classmethod
    def count_tokens(cls, text: str, model: str = "gpt-4-mini") -> int:
        """
        Contar tokens en un texto para un modelo específico
        
        Args:
            text: Texto a contar
            model: Modelo a usar
            
        Returns:
            Número de tokens
        """
        if not text:
            return 0
            
        encoder = cls.get_encoder(model)
        return len(encoder.encode(text))
    
    @classmethod
    def count_message_tokens(cls, messages: List[Dict[str, str]], model: str = "gpt-4-mini") -> int:
        """
        Contar tokens en una lista de mensajes para un modelo específico
        
        Args:
            messages: Lista de mensajes en formato OpenAI
            model: Modelo a usar
            
        Returns:
            Número de tokens
        """
        if not messages:
            return 0
            
        encoder = cls.get_encoder(model)
        num_tokens = 0
        
        # Tokens por mensaje y por función según la documentación de OpenAI
        tokens_per_message = 3
        tokens_per_name = 1
        
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                if key == "role" or key == "content":
                    if value:
                        num_tokens += len(encoder.encode(value))
                elif key == "name":
                    num_tokens += tokens_per_name
                    if value:
                        num_tokens += len(encoder.encode(value))
                        
        # Tokens de la respuesta
        num_tokens += 3  # Cada respuesta comienza con <|assistant|>
        
        return num_tokens
    
    @classmethod
    def check_context_limit(cls, tokens: int, model: str = "gpt-4-mini", buffer_percentage: float = 0.1) -> bool:
        """
        Verificar si el número de tokens está dentro del límite del contexto
        
        Args:
            tokens: Número de tokens
            model: Modelo a usar
            buffer_percentage: Porcentaje de buffer para la respuesta (0.1 = 10%)
            
        Returns:
            True si está dentro del límite, False si no
        """
        limit = cls.MODEL_CONTEXT_LIMITS.get(model, 4096)
        
        # Aplicar buffer para la respuesta
        adjusted_limit = int(limit * (1 - buffer_percentage))
        
        return tokens <= adjusted_limit
    
    @classmethod
    def truncate_text_to_token_limit(cls, text: str, model: str = "gpt-4-mini", max_tokens: int = None) -> str:
        """
        Truncar texto para que no supere un límite de tokens
        
        Args:
            text: Texto a truncar
            model: Modelo a usar
            max_tokens: Límite máximo de tokens (si es None, usa el límite del modelo con buffer)
            
        Returns:
            Texto truncado
        """
        if not text:
            return ""
            
        encoder = cls.get_encoder(model)
        
        if max_tokens is None:
            limit = cls.MODEL_CONTEXT_LIMITS.get(model, 4096)
            max_tokens = int(limit * 0.9)  # 90% del límite
        
        tokens = encoder.encode(text)
        
        if len(tokens) <= max_tokens:
            return text
            
        truncated_tokens = tokens[:max_tokens]
        return encoder.decode(truncated_tokens)
