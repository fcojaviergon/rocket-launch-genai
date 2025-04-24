from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union, AsyncGenerator, Optional, Generator

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
        response_format: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None, # Add max_tokens if needed commonly
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generates a chat completion response from the LLM.

        Args:
            messages: A list of message dictionaries (e.g., {'role': 'user', 'content': '...'}).
            model: The specific model identifier for the provider.
            temperature: Sampling temperature.
            response_format: Optional response format for structured output.
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
