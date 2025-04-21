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
    def generate_chat_completion_sync(
        self,
        messages: List[LLMMessage], 
        model: str, 
        temperature: float = 0.7, 
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[str, Generator[str, None, None]]:
        """
        Generates a chat completion response from the LLM synchronously.
        
        This method should be implemented for use in synchronous contexts
        where async/await cannot be used, such as in Celery tasks.

        Args:
            messages: A list of message dictionaries (e.g., {'role': 'user', 'content': '...'}).
            model: The specific model identifier for the provider.
            temperature: Sampling temperature.
            max_tokens: Optional maximum tokens to generate.
            stream: Whether to return a streaming generator or a single string response.

        Returns:
            Either the complete response content as a string (if stream=False),
            or a generator yielding response chunks (if stream=True).
            
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

    @abstractmethod
    def generate_embeddings_sync(
        self,
        texts: List[str],
        model: str
    ) -> List[List[float]]:
        """
        Generates embedding vectors for a list of texts synchronously.
        
        This method should be implemented for use in synchronous contexts
        where async/await cannot be used, such as in Celery tasks.

        Args:
            texts: A list of strings to embed.
            model: The specific embedding model identifier for the provider.

        Returns:
            A list of embedding vectors (list of floats), one for each input text.
            
        Raises:
            Exception: If the underlying API call fails.
        """
        pass
