# backend/core/anthropic_client.py
import logging
from typing import List, Dict, Any, Union, AsyncGenerator, Optional

# Import the Anthropic library
import anthropic

from core.config import settings
from core.llm_interface import LLMClientInterface, LLMMessage

logger = logging.getLogger(__name__)

class AnthropicClient(LLMClientInterface):
    """Concrete implementation of LLMClientInterface for Anthropic."""
    
    def __init__(self):
        self.client = None
        api_key = settings.ANTHROPIC_API_KEY # Assumes ANTHROPIC_API_KEY exists in settings
        if not api_key or api_key.strip() == "" or api_key == "None":
            logger.error("AnthropicClient: ANTHROPIC_API_KEY is not defined or empty.")
            # Don't raise error immediately, allow initialization without key if only other methods are used
            # Raise error during method call if client is needed but not initialized.
        else:
            try:
                # Anthropic client initialization (adjust if async client needs httpx)
                self.client = anthropic.Anthropic(api_key=api_key)
                # Or if async is needed: self.client = anthropic.AsyncAnthropic(api_key=api_key)
                logger.info("AnthropicClient initialized successfully.")
            except Exception as e:
                logger.error(f"AnthropicClient: Failed to initialize - {e}", exc_info=True)
                # Don't raise, let methods handle self.client being None

    async def generate_chat_completion(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 1024, # Anthropic requires max_tokens
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        if not self.client:
             raise RuntimeError("AnthropicClient is not initialized (Missing API Key?).")
             
        # --- Adapt messages to Anthropic format (system prompt + user/assistant turns) --- 
        system_prompt = ""
        anthropic_messages = []
        for msg in messages:
             if msg["role"] == "system":
                  system_prompt = msg["content"]
             else:
                  anthropic_messages.append(msg) # Anthropic uses 'user' and 'assistant'
        # ---------------------------------------------------------------------------

        try:
            logger.debug(f"Calling Anthropic completion: model={model}, stream={stream}")
            # Note: Anthropic SDK might have different method names or parameters
            # This is a placeholder - **NEEDS ACTUAL IMPLEMENTATION**
            # response = self.client.messages.create(...)
            raise NotImplementedError("Anthropic chat completion needs implementation.")

            # Placeholder for stream handling:
            # if stream:
            #     async def stream_generator():
            #         async for chunk in response:
            #             # Extract content from Anthropic chunk
            #             yield content
            #     return stream_generator()
            # else:
            #     # Extract full response content from Anthropic response
            #     return full_response

        except Exception as e:
            logger.error(f"Anthropic API error during chat completion: {e}", exc_info=True)
            raise

    async def generate_embeddings(
        self,
        texts: List[str],
        model: str
    ) -> List[List[float]]:
        if not self.client:
             raise RuntimeError("AnthropicClient is not initialized (Missing API Key?).")
             
        # Anthropic might not offer a direct embedding endpoint via this client
        # or might use a different model naming convention/API structure.
        logger.error("Anthropic embedding generation is not supported/implemented in this client.")
        raise NotImplementedError("Anthropic embedding generation is not implemented.") 