# backend/core/openai_client.py
import logging
from typing import List, Dict, Any, Union, AsyncGenerator, Optional, Generator

from openai import AsyncOpenAI, OpenAI
import httpx

from core.config import settings
from core.llm_interface import LLMClientInterface, LLMMessage # Import the interface

logger = logging.getLogger(__name__)

class OpenAIClient(LLMClientInterface):
    """Concrete implementation of LLMClientInterface for OpenAI."""
    
    def __init__(self):
        self.client = None
        self.sync_client = None
        self.default_model = "gpt-4o"
        self.default_embedding_model = "text-embedding-3-small"
        
        # Importar aquí para evitar importaciones circulares
        from core.token_counter import TokenCounter
        self.token_counter = TokenCounter
        
        api_key = settings.OPENAI_API_KEY
        if not api_key or api_key.strip() == "" or api_key == "None":
            logger.error("OpenAIClient: OPENAI_API_KEY is not defined or empty.")
            raise ValueError("OPENAI_API_KEY must be configured for OpenAIClient")
        else:
            try:
                # Consistent timeout handling for async client
                timeout = httpx.Timeout(60.0, connect=5.0)
                http_client = httpx.AsyncClient(timeout=timeout)
                self.client = AsyncOpenAI(api_key=api_key, http_client=http_client)
                
                # Initialize synchronous client too
                self.sync_client = OpenAI(api_key=api_key, timeout=60.0)
                
                logger.info("OpenAIClient initialized successfully (async and sync).")
            except Exception as e:
                logger.error(f"OpenAIClient: Failed to initialize clients - {e}", exc_info=True)
                # Propagate the error to prevent using a non-functional client
                raise RuntimeError(f"Failed to initialize OpenAI client: {e}") from e

    async def generate_chat_completion(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        user_id: Optional[str] = None
    ) -> Union[str, AsyncGenerator[str, None]]:
        if not self.client:
             raise RuntimeError("OpenAIClient is not initialized.")
        
        # Usar modelo por defecto si no se especifica
        model = model or self.default_model
        
        # Contar tokens en los mensajes para validar límites de contexto
        prompt_tokens = self.token_counter.count_message_tokens(messages, model)
        
        # Verificar si excede el límite de contexto
        if not self.token_counter.check_context_limit(prompt_tokens, model):
            error_msg = f"El prompt excede el límite de contexto del modelo {model} ({prompt_tokens} tokens)"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Verificar cuota de usuario si se proporciona ID
        if user_id:
            try:
                from database.session import get_async_session_context
                from core.token_usage_tracker import TokenUsageTracker
                
                # Obtener sesión de base de datos
                db = get_async_session_context()
                tracker = TokenUsageTracker(db)
                
                # Verificar cuota
                quota_check = await tracker.check_user_quota(user_id)
                
                if not quota_check.get("has_quota", True):
                    error_msg = f"Usuario {user_id} ha excedido su cuota mensual de tokens"
                    logger.error(error_msg)
                    await db.close()
                    raise ValueError(error_msg)
                    
                await db.close()
            except Exception as e:
                logger.error(f"Error al verificar cuota de usuario {user_id}: {e}")
                # Continuar si hay error en la verificación
        
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            "response_format": response_format
        }
        # Filter out None values for optional parameters like max_tokens
        request_params = {k: v for k, v in request_params.items() if v is not None}
        
        try:
            logger.debug(f"Calling OpenAI Chat Completions API: model={model}, stream={stream}, prompt_tokens={prompt_tokens}")
            response_or_stream = await self.client.chat.completions.create(**request_params)
            
            if stream:
                # Standard stream handling for chat completions
                async def stream_generator():
                    completion_tokens = 0
                    async for chunk in response_or_stream:
                        content_delta = chunk.choices[0].delta.content
                        if content_delta is not None:
                            # Contar tokens de la respuesta
                            completion_tokens += self.token_counter.count_tokens(content_delta, model)
                            yield content_delta
                    
                    # Registrar uso de tokens al final del stream si hay user_id
                    if user_id:
                        self._record_token_usage(user_id, model, prompt_tokens, completion_tokens, "chat_stream")
                        
                return stream_generator()
            else:
                # Standard non-streaming response handling
                full_response_content = response_or_stream.choices[0].message.content
                logger.debug(f"Received OpenAI Chat Completions API response: {full_response_content[:100]}...")
                
                # Registrar uso de tokens
                if user_id:
                    completion_tokens = response_or_stream.usage.completion_tokens
                    prompt_tokens = response_or_stream.usage.prompt_tokens
                    self._record_token_usage(user_id, model, prompt_tokens, completion_tokens, "chat")
                
                # Ensure string return, handle potential None case
                return full_response_content if full_response_content is not None else "" 

        except Exception as e:
            # Log the specific API error
            logger.error(f"OpenAI Chat Completions API error: {e}", exc_info=True)
            # Re-raise or handle specific OpenAI errors if needed
            raise

    async def _record_token_usage(self, user_id: str, model: str, prompt_tokens: int, completion_tokens: int, operation_type: str, metadata: dict = None):
        """
        Registrar uso de tokens en la base de datos
        
        Args:
            user_id: ID del usuario
            model: Modelo utilizado
            prompt_tokens: Tokens del prompt
            completion_tokens: Tokens de la respuesta
            operation_type: Tipo de operación (chat, embedding, etc.)
        """
        try:
            from database.session import get_async_session_context
            from core.token_usage_tracker import TokenUsageTracker
            
            # Obtener sesión de base de datos
            db = get_async_session_context()
            tracker = TokenUsageTracker(db)
            
            # Registrar uso
            usage_result = await tracker.record_usage(
                user_id=user_id,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                operation_type=operation_type
            )
            
            # Estimar costo
            cost = tracker.estimate_cost(model, prompt_tokens, completion_tokens)
            
            logger.info(f"Token usage recorded for user {user_id}: {prompt_tokens + completion_tokens} tokens, cost: ${cost['total_cost']:.6f}")
            
            db.close()
            return usage_result
        except Exception as e:
            logger.error(f"Error recording token usage: {e}")
            return {"recorded": False, "error": str(e)}
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: str = None,
        user_id: Optional[str] = None
    ) -> List[List[float]]:
        if not self.client:
             raise RuntimeError("OpenAIClient is not initialized.")
        
        # Usar modelo por defecto si no se especifica
        model = model or self.default_embedding_model
        
        # Contar tokens en los textos
        total_tokens = sum(self.token_counter.count_tokens(text, model) for text in texts)
        
        # Verificar cuota de usuario si se proporciona ID
        if user_id:
            try:
                from database.session import get_async_session_context
                from core.token_usage_tracker import TokenUsageTracker
                
                # Obtener sesión de base de datos
                db = get_async_session_context()
                tracker = TokenUsageTracker(db)
                
                # Verificar cuota
                quota_check = await tracker.check_user_quota(user_id)
                
                if not quota_check.get("has_quota", True):
                    error_msg = f"Usuario {user_id} ha excedido su cuota mensual de tokens"
                    logger.error(error_msg)
                    await db.close()
                    raise ValueError(error_msg)
                    
                await db.close()
            except Exception as e:
                logger.error(f"Error al verificar cuota de usuario {user_id}: {e}")
                # Continuar si hay error en la verificación
             
        try:
            logger.debug(f"Calling OpenAI embeddings: model={model}, num_texts={len(texts)}, total_tokens={total_tokens}")
            response = await self.client.embeddings.create(
                input=texts,
                model=model
            )
            embeddings = [item.embedding for item in response.data]
            logger.debug(f"Received {len(embeddings)} embeddings from OpenAI.")
            
            # Registrar uso de tokens
            if user_id:
                # En embeddings solo hay prompt tokens, no completion tokens
                prompt_tokens = response.usage.total_tokens
                await self._record_token_usage(user_id, model, prompt_tokens, 0, "embedding")
            
            return embeddings
        except Exception as e:
            logger.error(f"OpenAI API error during embedding generation: {e}", exc_info=True)
            raise