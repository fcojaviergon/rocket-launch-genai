from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union, AsyncGenerator, Optional

# Define common request/response structures if needed, or use basic types
# For example, a generic message format:
class LLMMessage(Dict):
    role: str
    content: str

class LLMClientInterface(ABC):
    """Abstract Base Class defining the interface for LLM clients."""

    @abstractmethod
    async def generate_chat_completion(
        self,
        messages: List[LLMMessage], 
        model: str, 
        temperature: float = 0.7, 
        max_tokens: Optional[int] = None, # Add max_tokens if needed commonly
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generates a chat completion response from the LLM.

        Args:
            messages: A list of message dictionaries (e.g., {'role': 'user', 'content': '...'}).
            model: The specific model identifier for the provider.
            temperature: Sampling temperature.
            max_tokens: Optional maximum tokens to generate.
            stream: Whether to return a streaming generator or a single string response.

        Returns:
            Either the complete response content as a string (if stream=False),
            or an async generator yielding response chunks (if stream=True).
            
        Raises:
            Exception: If the underlying API call fails.
        """
        pass

    @abstractmethod
    async def generate_embeddings(
        self,
        texts: List[str],
        model: str
    ) -> List[List[float]]:
        """
        Generates embedding vectors for a list of texts.

        Args:
            texts: A list of strings to embed.
            model: The specific embedding model identifier for the provider.

        Returns:
            A list of embedding vectors (list of floats), one for each input text.
            
        Raises:
            Exception: If the underlying API call fails.
        """
        pass

    async def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Simplified interface for non-streaming LLM chat completion.
        
        Args:
            messages: A list of message dictionaries with role and content.
            tools: Optional list of tools that can be called by the LLM.
            
        Returns:
            The complete response as a dictionary with the LLM's reply.
        """
        # Default implementation that can be overridden by subclasses
        model = self._get_default_model()
        return await self.generate_chat_completion(messages, model, stream=False)
        
    async def stream_chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Simplified interface for streaming LLM chat completion.
        
        Args:
            messages: A list of message dictionaries with role and content.
            tools: Optional list of tools that can be called by the LLM.
            
        Yields:
            Chunks of the LLM's response as they become available.
        """
        # Default implementation that can be overridden by subclasses
        model = self._get_default_model()
        # Get streaming generator - don't await here
        generator = self.generate_chat_completion(messages, model, stream=True)
        async for chunk in generator:
            yield chunk
            
    def _get_default_model(self) -> str:
        """Get the default model for this provider."""
        return "gpt-4o"  # Default model, should be overridden by subclasses

    # Add other abstract methods for different capabilities if needed later
    # e.g., generate_image, classify_text, etc. 