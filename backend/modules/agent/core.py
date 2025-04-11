from enum import Enum
from typing import Tuple, Dict, Callable, Any, List, AsyncIterator, Optional, AsyncGenerator, Union, Iterator
from modules.agent.state import AgentState
from services.agent_tools.registry import tool_registry
from core.config import settings
import logging
import json
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

logger = logging.getLogger(__name__)

# Constants for agent prompts
AGENT_DESCRIPTION = """You are a helpful AI assistant that can use tools to answer user queries."""
AGENT_INSTRUCTIONS = """Answer the user's questions as best you can. You have access to tools that you can use to get more information. When you use a tool, I'll show you the result so you can use it to form your response."""
AGENT_RESPONSE_FORMAT = """If you need to use a tool, you MUST use the exact following JSON format:

```json
{
  "tool": "tool_name",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}
```
If you don't need to use a tool, respond directly to the user's query. Be concise, helpful, and specific. Do not escape special characters like parentheses or asterisks in your responses - use characters like (, ), *, + as they are."""

# Enum for LLM response finish reasons
class FinishReason(str, Enum):
    """Reason for finishing a streaming response."""
    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALLS = "tool_calls"
    FUNCTION_CALL = "function_call"


async def run_agent_loop(
    agent_state: AgentState,
    db: Optional[AsyncSession] = None,
) -> AsyncGenerator[str, None]:
    """
    Run the main agent loop with streaming.
    
    Args:
        agent_state: The agent state containing the conversation history
        db: Optional database session for persisting messages
    
    Yields:
        str: Chunks of the assistant's response
    """
    # Import get_llm_client here to avoid circular import
    from core.dependencies import get_llm_client
    
    # Initialize LLM client
    client = get_llm_client()
    
    # Load available tools from registry
    available_tools = tool_registry.get_all_tools()
    
    # Build system prompt with tools
    system_prompt = build_system_prompt(available_tools)
    
    # Build history from agent state
    history = agent_state.get_history()
    
    # Set max iterations to prevent infinite loops
    max_iterations = 3
    iteration = 0
    
    try:
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Starting iteration {iteration}/{max_iterations}")
            
            # Prepare messages for LLM
            messages = prepare_messages(system_prompt, history)
            
            # Stream response and handle tool calls
            collected_response = ""
            is_tool_call = False
            
            try:
                async for chunk in client.stream_chat(messages=messages, tools=available_tools):
                    # Process the chunk based on its format
                    if isinstance(chunk, dict) and "choices" in chunk:
                        # OpenAI style chunks
                        for choice in chunk.get("choices", []):
                            delta = choice.get("delta", {})
                            finish_reason = choice.get("finish_reason")
                            
                            # Handle content
                            if "content" in delta and delta["content"]:
                                content = delta["content"]
                                collected_response += content
                                yield content
                            
                            # Check for tool calls in OpenAI format
                            if "tool_calls" in delta and delta["tool_calls"] or finish_reason == FinishReason.TOOL_CALLS:
                                is_tool_call = True
                                break
                    elif isinstance(chunk, str) and chunk:
                        # Simple text chunks (Anthropic style)
                        collected_response += chunk
                        yield chunk
            except Exception as e:
                logger.error(f"Error during streaming: {e}", exc_info=True)
                error_msg = f"Error during streaming: {str(e)}"
                yield error_msg
                collected_response = error_msg
            
            # If we have a complete response without tool calls, we're done
            if not is_tool_call and collected_response and not collected_response.startswith("Error:"):
                # Persist the response
                if db:
                    try:
                        await agent_state.add_llm_response(collected_response)
                        await db.commit()
                        logger.info("Agent response persisted to database")
                    except Exception as e:
                        logger.error(f"Error persisting agent response: {e}", exc_info=True)
                        await db.rollback()
                    finally:
                        # Ensure connection is returned to the pool
                        await db.close()
                
                logger.info(f"Agent response complete after {iteration} iterations")
                logger.info("Generated valid response, exiting loop early")
                break
            
            # If we detected a tool call, handle it
            if is_tool_call:
                # Get the non-streaming version to extract tool calls
                try:
                    tool_call_response = await client.chat(messages=messages, tools=available_tools)
                    
                    # Extract and process tool calls
                    tool_calls = extract_tool_calls(tool_call_response)
                    if tool_calls:
                        logger.info(f"Found {len(tool_calls)} tool calls to execute: {[tc.get('name') for tc in tool_calls]}")
                        
                        # Execute each tool call
                        for tool_call in tool_calls:
                            tool_name = tool_call.get("name")
                            arguments = tool_call.get("arguments", {})
                            
                            if not tool_name:
                                logger.error("Tool name is missing")
                                continue
                                
                            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
                            
                            # Convert arguments to proper format
                            if isinstance(arguments, str):
                                try:
                                    arguments = json.loads(arguments)
                                except json.JSONDecodeError:
                                    arguments = {"input": arguments}
                            
                            # Get the tool
                            tool = tool_registry.get_tool_by_name(tool_name)
                            if not tool:
                                logger.error(f"Tool '{tool_name}' not found in registry")
                                continue
                            
                            # Execute the tool with timeout
                            try:
                                logger.info(f"Executing tool with timeout: {tool_name}")
                                start_time = asyncio.get_event_loop().time()
                                
                                # Aumentar timeout para herramientas MCP
                                tool_timeout = 120.0
                                
                                tool_result = await asyncio.wait_for(
                                    tool.arun(**arguments),
                                    timeout=tool_timeout
                                )
                                elapsed = asyncio.get_event_loop().time() - start_time
                                logger.info(f"Tool execution completed in {elapsed:.2f} seconds")
                                
                                # Yield tool execution result to user
                                tool_result_msg = f"Successfully executed {tool_name}. Result: {tool_result}"
                                yield tool_result_msg
                                
                                # Add tool call to agent state
                                await agent_state.add_action_and_observation(
                                    action=f"{tool_name}({json.dumps(arguments)})",
                                    observation=tool_result
                                )
                                
                                # After tool execution, immediately ask for final answer
                                logger.info("Requesting final answer after tool execution")
                                
                                # Create prompt for final answer
                                final_messages = messages.copy()
                                final_messages.append({
                                    "role": "assistant",
                                    "content": f"I'll use the {tool_name} tool."
                                })
                                final_messages.append({
                                    "role": "user",
                                    "content": f"Tool result: {tool_result}\n\nNow please provide your final answer based on this result."
                                })
                                
                                # Get final answer
                                final_response = ""
                                async for chunk in client.stream_chat(messages=final_messages, tools=None):
                                    if isinstance(chunk, dict) and "choices" in chunk:
                                        for choice in chunk.get("choices", []):
                                            delta = choice.get("delta", {})
                                            if "content" in delta and delta["content"]:
                                                content = delta["content"]
                                                final_response += content
                                                yield content
                                    elif isinstance(chunk, str) and chunk:
                                        final_response += chunk
                                        yield chunk
                                
                                # Persist final answer
                                if final_response:
                                    await agent_state.add_llm_response(final_response)
                                    # Explicitly commit and close the session to prevent connection leaks
                                    if db:
                                        try:
                                            await db.commit()
                                            logger.info("Final answer persisted to database")
                                        except Exception as e:
                                            logger.error(f"Error committing final answer: {e}", exc_info=True)
                                            await db.rollback()
                                        finally:
                                            # Ensure connection is returned to the pool
                                            await db.close()
                                    return  # Exit the function with successful response
                                
                            except asyncio.TimeoutError:
                                logger.error(f"Tool execution timed out: {tool_name}")
                                error_msg = f"Error: {tool_name} execution timed out after {tool_timeout} seconds"
                                yield error_msg
                            except Exception as e:
                                logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                                yield f"Error: Failed to execute {tool_name}"
                    else:
                        logger.info("No tool calls found in response")
                        
                        # If we thought it was a tool call but none were found, treat as regular response
                        if "choices" in tool_call_response and len(tool_call_response["choices"]) > 0:
                            content = tool_call_response["choices"][0]["message"].get("content", "")
                            if content and not collected_response:
                                collected_response = content
                                yield content
                                
                                # Persist this response
                                await agent_state.add_llm_response(collected_response)
                                try:
                                    await db.commit()
                                    logger.info("Regular response persisted to database")
                                except Exception as e:
                                    logger.error(f"Error persisting response: {e}", exc_info=True)
                                    await db.rollback()
                                finally:
                                    # Ensure connection is returned to the pool
                                    if db:
                                        await db.close()
                                return  # Exit with this response
                
                except Exception as e:
                    logger.error(f"Error handling tool call: {e}", exc_info=True)
                    yield f"Error handling tool call: {str(e)}"
            
            # Update history for next iteration if needed
            history = agent_state.get_history()
            
        # If we've reached max iterations without a response
        if iteration >= max_iterations and not collected_response:
            logger.warning(f"Reached maximum iterations ({max_iterations}) without complete response")
            yield "I apologize, but I wasn't able to generate a complete response. Please try rephrasing your question."
            
        # Ensure database connection is released at the end
        if db:
            try:
                await db.close()
                logger.debug("Database connection properly closed at end of agent loop")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
    
    except Exception as e:
        logger.error(f"Unexpected error in agent loop: {e}", exc_info=True)
        yield f"Error: {str(e)}"
        
        # Ensure database connection is released even on error
        if db:
            try:
                await db.close()
                logger.debug("Database connection properly closed after error")
            except Exception as close_e:
                logger.error(f"Error closing database connection after error: {close_e}")

def build_system_prompt(tools: List[Any]) -> str:
    """Build the system prompt with tools description."""
    # Basic agent description and instructions
    prompt = f"{AGENT_DESCRIPTION}\n\n{AGENT_INSTRUCTIONS}\n\n"

    # Add tools if available
    if tools:
        prompt += "You have access to the following tools:\n\n"
        for tool in tools:
            # Modify the MCP tool description directly here if needed (simpler approach)
            if tool.name == "mcp":
                 prompt += f"- {tool.name}: {tool.description} \n"
                 # Add the general hint directly after the main MCP tool description
                 # Removed the hint from the property itself to keep it cleaner
                 hint = "IMPORTANT: For complex tasks like web scraping or search, check command parameters carefully. Optional parameters (e.g., 'formats', 'onlyMainContent', 'waitFor', 'limit') might be crucial for quality results even if not strictly required by the schema.\n"
                 prompt += f"  {hint}\n"
            else:
                prompt += f"- {tool.name}: {tool.description}\n"   
        
        prompt += "\n"
            
    # Add response format instructions
    prompt += AGENT_RESPONSE_FORMAT

    return prompt

def prepare_messages(system_prompt: str, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Prepare messages for the LLM client."""
    messages = [{"role": "system", "content": system_prompt}]
    
    for item in history:
        # Handle different message types from history
        role = item.get("role", "")
        content = item.get("content", "")
        
        if role == "user":
            messages.append({"role": "user", "content": content})
        elif role == "assistant":
            messages.append({"role": "assistant", "content": content})
        elif role == "action":
            # For tool calls, we represent them as assistant responses with function call and observation as user response
            action_content = f"I'll execute the tool {content}"
            messages.append({"role": "assistant", "content": action_content})
        elif role == "observation":
            # Tool results are represented as user messages
            observation_content = f"Tool result: {content}"
            messages.append({"role": "user", "content": observation_content})
    
    return messages

def extract_tool_calls(response: Union[Dict[str, Any], str]) -> List[Dict[str, Any]]:
    """Extract tool calls from the LLM response."""
    tool_calls = []
    
    if isinstance(response, dict):
        # Extract from OpenAI style response
        if "choices" in response and len(response["choices"]) > 0:
            message = response.get("choices", [{}])[0].get("message", {})
            
            # Check for OpenAI tool_calls
            if message is not None and "tool_calls" in message:
                tool_calls_data = message.get("tool_calls")
                # Ensure tool_calls_data is iterable before trying to iterate
                if tool_calls_data is not None and isinstance(tool_calls_data, list):
                    for tool_call in tool_calls_data:
                        function = tool_call.get("function", {})
                        tool_calls.append({
                            "name": function.get("name", ""),
                            "arguments": function.get("arguments", {})
                        })
            
            # Check for content with custom JSON format
            elif message is not None and "content" in message:
                content = message.get("content", "")
                # Try to extract JSON blocks
                tool_calls.extend(extract_json_tool_calls_from_content(content))
    
    return tool_calls

def extract_json_tool_calls_from_content(content: str) -> List[Dict[str, Any]]:
    """Extract tool calls from JSON blocks in content."""
    import re
    import json
    
    tool_calls = []
    
    # Find JSON blocks in triple backticks
    json_pattern = r"```json\s*([\s\S]*?)\s*```"
    matches = re.findall(json_pattern, content)
    
    for json_str in matches:
        try:
            # Parse the JSON
            data = json.loads(json_str)
            
            # Validate it has required fields
            if "tool" in data and "parameters" in data:
                tool_calls.append({
                    "name": data["tool"],
                    "arguments": data["parameters"]
                })
        except Exception as e:
            logger.error(f"Error parsing JSON tool call: {e}")
    
    return tool_calls
