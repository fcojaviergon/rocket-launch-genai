from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
import httpx
from core.config import settings
from core.llm_interface import LLMClientInterface, LLMMessage

class CompletionService:
    """Service to generate text completions with LLMs"""
    
    def __init__(self, llm_client: LLMClientInterface):
        self.llm_client = llm_client
        self.default_model = settings.DEFAULT_CHAT_MODEL or "gpt-4"

    async def generate_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = 500,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate a text completion using the configured LLM client.
        
        Args:
            prompt: Initial text for the completion
            model: Model to use (default: from settings or gpt-4)
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for sampling (0-1)
            
        Returns:
            The generated text completion as a string.
        """
        try:
            messages: List[LLMMessage] = [{"role": "user", "content": prompt}]
            
            completion_text = await self.llm_client.generate_chat_completion(
                messages=messages,
                model=model or self.default_model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            return completion_text
            
        except Exception as e:
            print(f"Error generating completion: {str(e)}")
            raise
