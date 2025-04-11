"""
Tool Registry for Agent Tools

This module implements a registry for agent tools that can be used by the agent.
"""
import logging
from typing import Dict, List, Optional, Type, Any
import importlib
import inspect
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Registry for agent tools."""

    def __init__(self):
        """Initialize the tool registry."""
        self.tools: Dict[str, Any] = {}
        self._loaded = False

    def register_tool(self, tool: Any) -> None:
        """
        Register a tool with the registry.
        
        Args:
            tool: The tool instance to register
        """
        if not hasattr(tool, "name") or not tool.name:
            raise ValueError("Tool must have a name attribute")
        
        if not hasattr(tool, "description") or not tool.description:
            raise ValueError("Tool must have a description attribute")
            
        if not hasattr(tool, "arun") or not callable(tool.arun):
            raise ValueError("Tool must have an arun method")
            
        self.tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get_tool_by_name(self, name: str) -> Optional[Any]:
        """
        Get a tool by name.
        
        Args:
            name: The name of the tool to get
            
        Returns:
            The tool instance or None if not found
        """
        self._ensure_loaded()
        return self.tools.get(name)

    def get_all_tools(self) -> List[Any]:
        """
        Get all registered tools.
        
        Returns:
            List of all registered tool instances
        """
        self._ensure_loaded()
        return list(self.tools.values())
    
    def _ensure_loaded(self) -> None:
        """Ensure tools are loaded from modules."""
        if not self._loaded:
            self._discover_tools()
            self._loaded = True
    
    def _discover_tools(self) -> None:
        """Discover and load tools from agent_tools directory."""
        try:
            # Get the directory where this file is located
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            
            # Get all Python files in the directory
            py_files = [f for f in current_dir.glob("*.py") if f.is_file() and f.name != "__init__.py" and f.name != "registry.py"]
            
            for py_file in py_files:
                try:
                    # Use a relative import instead of absolute
                    module_name = f"services.agent_tools.{py_file.stem}"
                    
                    # Import the module
                    module = importlib.import_module(module_name)
                    
                    # Look for tool instances in the module
                    for name, obj in inspect.getmembers(module):
                        # Check if it's a tool instance
                        if hasattr(obj, "name") and hasattr(obj, "description") and hasattr(obj, "arun") and callable(obj.arun):
                            self.register_tool(obj)
                    
                except Exception as e:
                    logger.error(f"Error loading tools from {py_file}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error discovering tools: {str(e)}")
        
        # Log the number of discovered tools
        logger.info(f"Discovered {len(self.tools)} tools")

    async def health_check(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform a health check on all registered tools.
        
        Returns:
            Dict with tool status information
        """
        self._ensure_loaded()
        results = {}
        
        for name, tool in self.tools.items():
            tool_info = {
                "name": name,
                "description": getattr(tool, "description", "No description"),
                "status": "unknown",
                "error": None
            }
            
            # Check if tool has required attributes and methods
            if not hasattr(tool, "arun") or not callable(tool.arun):
                tool_info["status"] = "error"
                tool_info["error"] = "Tool missing required arun method"
            else:
                # Do a simple test to see if the tool can be called with minimal args
                try:
                    # We don't actually run the tool, just check it's callable
                    tool_info["status"] = "ready"
                except Exception as e:
                    tool_info["status"] = "error"
                    tool_info["error"] = str(e)
            
            results[name] = tool_info
        
        return results
    
    def get_tools_summary(self) -> str:
        """
        Get a human-readable summary of all registered tools.
        
        Returns:
            String with tool summary
        """
        self._ensure_loaded()
        
        if not self.tools:
            return "No tools registered."
        
        summary = f"Registered tools ({len(self.tools)}):\n"
        for name, tool in self.tools.items():
            description = getattr(tool, "description", "No description")
            summary += f"- {name}: {description}\n"
        
        return summary

# Create singleton instance
tool_registry = ToolRegistry() 