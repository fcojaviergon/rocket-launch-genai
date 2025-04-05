from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
import httpx
from core.config import settings

class CompletionService:
    """Service to generate text completions with LLMs"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.default_model = "gpt-4"
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            http_client=httpx.AsyncClient()
        )
        
    async def generate_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a text completion using the OpenAI API.
        
        Args:
            prompt: Initial text for the completion
            model: Model to use (default: gpt-4)
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for sampling (0-1)
            top_p: Cumulative probability for nucleus sampling
            frequency_penalty: Frequency penalty for tokens
            presence_penalty: Presence penalty for tokens
            stop: Sequences that stop the generation
            
        Returns:
            Response with the generated text
        """
        try:
            # Configure parameters for the API
            completion_params = {
                "model": model or self.default_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty
            }
            
            if stop:
                completion_params["stop"] = stop
                
            # Call the OpenAI API
            print(f"Calling OpenAI with model: {completion_params['model']}")
            response = await self.client.chat.completions.create(**completion_params)
            
            # Extract and return the generated text
            return {
                "text": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "finish_reason": response.choices[0].finish_reason
            }
            
        except Exception as e:
            # Register the error and rethrow it
            print(f"Error generating completion: {str(e)}")
            raise
