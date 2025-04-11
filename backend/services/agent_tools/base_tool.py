from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseTool(ABC):
    """Base class for all agent tools."""
    
    name = "base_tool"
    description = "Base tool class."
    
    def __init__(self):
        """Initialize the base tool."""
        pass
        
    @abstractmethod
    async def arun(self, **kwargs) -> str:
        """
        Execute the tool asynchronously.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            Result of the tool execution as a string
        """
        pass 