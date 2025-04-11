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

    async def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Execute a non-streaming chat completion with tools support.
        
        Args:
            messages: List of message dictionaries with role and content
            tools: Optional list of tools that can be used by the LLM
            
        Returns:
            A dictionary with the complete response
        """
        if not self.client:
            raise RuntimeError("OpenAIClient is not initialized.")
            
        model = self._get_default_model()
        
        # Convert tools to the format expected by OpenAI
        openai_tools = None
        if tools:
            openai_tools = [self._convert_tool_to_openai_format(tool) for tool in tools]
        
        try:
            params = {
                "model": model,
                "messages": messages,
                "temperature": 0.7
            }
            
            if openai_tools:
                params["tools"] = openai_tools
                params["tool_choice"] = "auto"
                
            logger.debug(f"Calling OpenAI Chat Completions API: {params}")
            
            response = await self.client.chat.completions.create(**params)
            response_dict = response.model_dump()
            
            # Ensure response has the expected structure
            if not response_dict.get("choices") or not response_dict["choices"][0].get("message"):
                logger.warning("Malformed response from OpenAI API")
                response_dict = {
                    "choices": [{
                        "message": {"content": "The model response was malformed."},
                        "finish_reason": "stop"
                    }]
                }
                
            return response_dict
            
        except Exception as e:
            logger.error(f"Error in OpenAI chat completion: {e}", exc_info=True)
            # Return a properly formatted error response instead of raising
            return {
                "choices": [{
                    "message": {"content": f"Error: {str(e)}"},
                    "finish_reason": "error"
                }]
            }
            
    async def stream_chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a streaming chat completion with tools support.
        
        Args:
            messages: List of message dictionaries with role and content
            tools: Optional list of tools that can be used by the LLM
            
        Yields:
            Chunks of the response as they arrive
        """
        if not self.client:
            raise RuntimeError("OpenAIClient is not initialized.")
            
        model = self._get_default_model()
        
        # Convert tools to the format expected by OpenAI
        openai_tools = None
        if tools:
            openai_tools = [self._convert_tool_to_openai_format(tool) for tool in tools]
        
        try:
            params = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "stream": True
            }
            
            if openai_tools:
                params["tools"] = openai_tools
                params["tool_choice"] = "auto"
                
            logger.debug(f"Calling OpenAI Chat Completions API (streaming): {params}")
            
            stream = await self.client.chat.completions.create(**params)
            
            # Ensure we have at least one valid chunk
            has_yielded_content = False
            
            async for chunk in stream:
                if chunk:
                    has_yielded_content = True
                    yield chunk.model_dump()
                    
            # If no content was yielded, provide a fallback empty chunk
            if not has_yielded_content:
                logger.warning("No content yielded from OpenAI streaming response")
                yield {"choices": [{"delta": {"content": ""}}], "finish_reason": "stop"}
                
        except Exception as e:
            logger.error(f"Error in OpenAI streaming chat completion: {e}", exc_info=True)
            # Yield an error chunk that can be handled by the frontend
            yield {"choices": [{"delta": {"content": f"Error: {str(e)}"}}], "finish_reason": "error"}
            raise
            
    def _convert_tool_to_openai_format(self, tool: Any) -> Dict[str, Any]:
        """Convert an agent tool to OpenAI function calling format."""
        # Get parameters from tool docstring or schema
        parameters = getattr(tool, "parameters", None)
        
        # If no parameters are defined, create a default schema based on the tool name
        if not parameters:
                # Generic parameters for other tools
                parameters = {
                    "type": "object",
                    "properties": {
                        "input": {
                            "type": "string",
                            "description": "Input for the tool"
                        }
                    },
                    "required": ["input"]
                }
        
        function = {
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters
        }
        
        return {"type": "function", "function": function}
            
    def _get_default_model(self) -> str:
        """Get the default model for this provider."""
        return "gpt-4o"

    async def generate_chat_completion(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 35000,
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