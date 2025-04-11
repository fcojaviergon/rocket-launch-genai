import asteval
import math
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Create an Interpreter instance
# We can pre-load safe functions and constants
aeval = asteval.Interpreter()

# Optionally disable certain symbols if needed for extra safety,
# but asteval is generally safe by default.
# Example: del aeval.symtable['while'] 

class CalculatorTool:
    """A tool for performing mathematical calculations."""
    
    name = "calculator"
    description = "Evaluates a mathematical expression. Supports basic arithmetic, parentheses, and common functions like sqrt(), sin(), cos(), log(), etc."
    
    async def arun(self, expression: str = None, **kwargs) -> str:
        """
        Safely evaluates a mathematical expression string using asteval.
        
        Args:
            expression: The mathematical expression to evaluate
            **kwargs: Additional arguments that might be passed
            
        Returns:
            The result of the calculation as a string
        """
        # Try to find the expression from various possible sources
        if not expression:
            # Check for common alternative argument names
            expression = kwargs.get('input') or kwargs.get('query') or kwargs.get('formula') or ''
            
        if not expression or not isinstance(expression, str):
            return "Error: Missing or invalid 'expression' argument. Please provide a mathematical expression to evaluate."
        
        logger.info(f"Attempting to calculate: {expression}")
        
        try:
            # Evaluate the expression using the Interpreter instance
            result = aeval(expression)
            
            # Check for potential errors returned by asteval
            if aeval.error:
                error_msg = "".join(err.get_error()[1] for err in aeval.error)
                aeval.error = [] # Clear errors for next evaluation
                logger.error(f"asteval error calculating '{expression}': {error_msg}")
                return f"Error evaluating expression: {error_msg}"
                
            # Check if result is a number (float, int) before formatting
            if isinstance(result, (int, float)):
                 # Format nicely, handling potential floating point inaccuracies if needed
                 # For simplicity, convert directly to string
                return str(result)
            else:
                # Handle cases where evaluation might return non-numeric types (should be rare with math)
                logger.warning(f"Evaluation of '{expression}' resulted in non-numeric type: {type(result).__name__}")
                return f"Evaluation resulted in non-numeric type: {type(result).__name__}"
                
        except Exception as e:
            # Catch unexpected errors during evaluation
            logger.error(f"Unexpected error calculating '{expression}': {e}", exc_info=True)
            return f"Error: An unexpected error occurred while evaluating the expression: {e}"


# Create a singleton instance of the calculator tool
calculator_tool = CalculatorTool()

def get_calculator_tool_description() -> str:
    # This function is now less critical as schema is defined in core.py
    # Kept for potential informational use.
    return "Evaluates a mathematical expression. Supports basic arithmetic, parentheses, and common functions like sqrt(), sin(), cos(), log(), etc."

def get_calculator_tool_description_old() -> str:
    """
    Returns a description of the Calculator tool for the LLM prompt.
    """
    return """
    calculator(action_string: str):
        Purpose: Evaluates a mathematical expression.
        action_string format: A standard mathematical expression (e.g., "(10 + 5) / 3", "sqrt(16) * 2").
        Supports basic arithmetic (+, -, *, /), parentheses, and common functions like sqrt(), sin(), cos(), log(), etc.
        Example call: calculator(action_string="(22 / 7) * 5^2")
    """ 