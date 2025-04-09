# backend/core/openai_client.py
import logging
from typing import List, Dict, Any, Union, AsyncGenerator, Optional

from openai import AsyncOpenAI
import httpx

from core.config import settings
from core.llm_interface import LLMClientInterface, LLMMessage # Import the interface

logger = logging.getLogger(__name__)

class OpenAIClient(LLMClientInterface):
    """Concrete implementation of LLMClientInterface for OpenAI."""
    
    def __init__(self):
        self.client = None
        api_key = settings.OPENAI_API_KEY
        if not api_key or api_key.strip() == "" or api_key == "None":
            logger.error("OpenAIClient: OPENAI_API_KEY is not defined or empty.")
            raise ValueError("OPENAI_API_KEY must be configured for OpenAIClient")
        else:
            try:
                # Consistent timeout handling
                timeout = httpx.Timeout(60.0, connect=5.0)
                http_client = httpx.AsyncClient(timeout=timeout)
                self.client = AsyncOpenAI(api_key=api_key, http_client=http_client)
                logger.info("OpenAIClient initialized successfully.")
            except Exception as e:
                logger.error(f"OpenAIClient: Failed to initialize AsyncOpenAI - {e}", exc_info=True)
                # Propagate the error to prevent using a non-functional client
                raise RuntimeError(f"Failed to initialize OpenAI client: {e}") from e

    async def generate_chat_completion(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        if not self.client:
             raise RuntimeError("OpenAIClient is not initialized.")
             
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        # Filter out None values for optional parameters like max_tokens
        request_params = {k: v for k, v in request_params.items() if v is not None}
        
        try:
            logger.debug(f"Calling OpenAI Chat Completions API: model={model}, stream={stream}, messages={messages}")
            response_or_stream = await self.client.chat.completions.create(**request_params)
            
            if stream:
                # Standard stream handling for chat completions
                async def stream_generator():
                    async for chunk in response_or_stream:
                        content_delta = chunk.choices[0].delta.content
                        if content_delta is not None:
                            yield content_delta
                return stream_generator()
            else:
                # Standard non-streaming response handling
                full_response_content = response_or_stream.choices[0].message.content
                logger.debug(f"Received OpenAI Chat Completions API response: {full_response_content[:100]}...")
                # Ensure string return, handle potential None case
                return full_response_content if full_response_content is not None else "" 

        except Exception as e:
            # Log the specific API error
            logger.error(f"OpenAI Chat Completions API error: {e}", exc_info=True)
            # Re-raise or handle specific OpenAI errors if needed
            raise

    async def generate_embeddings(
        self,
        texts: List[str],
        model: str
    ) -> List[List[float]]:
        if not self.client:
             raise RuntimeError("OpenAIClient is not initialized.")
             
        try:
            logger.debug(f"Calling OpenAI embeddings: model={model}, num_texts={len(texts)}")
            response = await self.client.embeddings.create(
                input=texts,
                model=model
            )
            embeddings = [item.embedding for item in response.data]
            logger.debug(f"Received {len(embeddings)} embeddings from OpenAI.")
            return embeddings
        except Exception as e:
            logger.error(f"OpenAI API error during embedding generation: {e}", exc_info=True)
            raise 