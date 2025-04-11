"""
Router for agent-related endpoints.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession


from core.dependencies import get_db, get_current_user
from core.dependencies import get_agent_service
from modules.agent.service import AgentService
from schemas.agent import (
    AgentConversation as AgentConversationSchema,
    AgentMessage as AgentMessageSchema,
    AgentQuery,
    AgentConversationCreate,
)
from schemas.user import UserResponse as User
from services.agent_tools.registry import tool_registry


router = APIRouter()


@router.post("/invoke", response_model=None)
async def invoke_agent(
    query: AgentQuery,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
):
    """
    Invoke the agent with a query and stream the response.
    
    Args:
        query: The user's query
        user: The authenticated user
        db: Database session
        agent_service: The agent service
        
    Returns:
        StreamingResponse: A streaming response with the agent's response
    """
    # Get conversation_id from the query model
    conversation_id = query.conversation_id
    
    async def stream_generator():
        try:
            async for chunk in agent_service.run_agent_with_streaming(
                db=db,
                conversation_id=conversation_id,
                query=query.query,
                user_id=user.id
            ):
                # Format the chunk for SSE
                yield f"data: {chunk}\n\n"
        except Exception as e:
            # Log the error
            import logging
            logging.error(f"Error during agent streaming: {str(e)}")
            # Yield an error message to the client
            yield f"data: {{\"error\": \"{str(e)}\", \"done\": true}}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )


@router.get("/conversations", response_model=List[AgentConversationSchema])
async def get_conversations(
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
):
    """
    Get all conversations for the authenticated user.
    
    Args:
        skip: Number of conversations to skip
        limit: Maximum number of conversations to return
        user: The authenticated user
        db: Database session
        agent_service: The agent service
        
    Returns:
        List[AgentConversationSchema]: A list of conversations
    """
    return await agent_service.get_conversations_by_user(db, user.id, skip, limit)


@router.get("/conversations/{conversation_id}", response_model=AgentConversationSchema)
async def get_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
):
    """
    Get a specific conversation.
    
    Args:
        conversation_id: The ID of the conversation to get
        user: The authenticated user
        db: Database session
        agent_service: The agent service
        
    Returns:
        AgentConversationSchema: The conversation
    """
    conversation = await agent_service.get_conversation(db, conversation_id, user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found",
        )
    
    return conversation


@router.put("/conversations/{conversation_id}/title", response_model=AgentConversationSchema)
async def update_conversation_title(
    conversation_id: UUID,
    title: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
):
    """
    Update the title of a conversation.
    
    Args:
        conversation_id: The ID of the conversation to update
        title: The new title
        user: The authenticated user
        db: Database session
        agent_service: The agent service
        
    Returns:
        AgentConversationSchema: The updated conversation
    """
    conversation = await agent_service.update_conversation_title(db, conversation_id, title, user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found",
        )
    
    return conversation


@router.delete("/conversations/{conversation_id}", response_model=bool)
async def delete_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
):
    """
    Delete a conversation.
    
    Args:
        conversation_id: The ID of the conversation to delete
        user: The authenticated user
        db: Database session
        agent_service: The agent service
        
    Returns:
        bool: True if the conversation was deleted
    """
    result = await agent_service.delete_conversation(db, conversation_id, user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found",
        )
    
    return result


@router.get("/conversations/{conversation_id}/messages", response_model=List[AgentMessageSchema])
async def get_messages(
    conversation_id: UUID,
    skip: int = 0,
    limit: int = 1000,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
):
    """
    Get all messages for a conversation.
    
    Args:
        conversation_id: The ID of the conversation
        skip: Number of messages to skip
        limit: Maximum number of messages to return
        user: The authenticated user
        db: Database session
        agent_service: The agent service
        
    Returns:
        List[AgentMessageSchema]: The messages
    """
    return await agent_service.get_messages_by_conversation(
        db, conversation_id, user_id=user.id, skip=skip, limit=limit
    )


@router.get("/conversations/{conversation_id}/detailed-messages", response_model=List[AgentMessageSchema])
async def get_detailed_messages(
    conversation_id: UUID,
    include_thinking: bool = False,
    include_tool_calls: bool = True,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
):
    """
    Get all messages for a conversation with option to include thinking steps.
    
    Args:
        conversation_id: The ID of the conversation
        include_thinking: Whether to include thinking messages (default: False)
        include_tool_calls: Whether to include tool call messages (default: True)
        user: The authenticated user
        db: Database session
        agent_service: The agent service
        
    Returns:
        List[AgentMessageSchema]: The detailed messages
    """
    # Get all messages including thinking steps
    messages = await agent_service.get_messages_by_conversation(
        db, conversation_id, user_id=user.id
    )
    
    # Filter based on parameters
    filtered_messages = []
    for message in messages:
        if message.role == "thinking" and not include_thinking:
            continue
        if message.role == "tool" and not include_tool_calls:
            continue
        filtered_messages.append(message)
    
    return filtered_messages


@router.post("/conversations", response_model=AgentConversationSchema)
async def create_conversation(
    title: str = "New Conversation",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
):
    """
    Create a new conversation.
    
    Args:
        title: Title for the new conversation
        user: The authenticated user
        db: Database session
        agent_service: The agent service
        
    Returns:
        AgentConversationSchema: The created conversation
    """
    conversation_data = AgentConversationCreate(title=title, user_id=user.id)
    return await agent_service.create_conversation(db, conversation_data)


@router.get("/diagnostics/tools", response_model=dict)
async def get_tool_diagnostics(
    user: User = Depends(get_current_user),
):
    """
    Get diagnostics information about available agent tools.
    Only accessible by authenticated users.
    
    Args:
        user: The authenticated user
        
    Returns:
        dict: Diagnostic information about tools
    """
    if not user.is_superuser:
        # For security, limit detailed diagnostics to superusers
        # Return a simplified summary for regular users
        summary = tool_registry.get_tools_summary()
        return {"summary": summary, "tools_count": len(tool_registry.tools)}
    
    # Full diagnostics for superusers
    tool_info = await tool_registry.health_check()
    
    return {
        "status": "ok",
        "tools_count": len(tool_info),
        "tools": tool_info,
        "summary": tool_registry.get_tools_summary()
    }


@router.post("/diagnostics/test-tool/{tool_name}")
async def test_specific_tool(
    tool_name: str,
    parameters: dict,
    user: User = Depends(get_current_user),
):
    """
    Test a specific tool with the given parameters.
    Only accessible by superusers for security.
    
    Args:
        tool_name: Name of the tool to test
        parameters: Parameters to pass to the tool
        user: The authenticated user
        
    Returns:
        dict: Result of the tool execution
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can test tools directly"
        )
    
    tool = tool_registry.get_tool_by_name(tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool {tool_name} not found"
        )
    
    try:
        result = await tool.arun(**parameters)
        return {
            "status": "success",
            "tool": tool_name,
            "parameters": parameters,
            "result": result
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return {
            "status": "error",
            "tool": tool_name,
            "parameters": parameters,
            "error": str(e),
            "traceback": tb
        }


@router.get("/mcp/servers", response_model=dict)
async def get_mcp_servers(
    user: User = Depends(get_current_user),
):
    """
    Get information about available MCP servers and their commands.
    This endpoint provides dynamic information for the frontend.
    
    Args:
        user: The authenticated user
        
    Returns:
        dict: Information about available MCP servers
    """
    # Get the MCP tool
    mcp_tool = tool_registry.get_tool_by_name("mcp")
    if not mcp_tool:
        return {
            "status": "error",
            "message": "MCP tool not available",
            "servers": {}
        }
    
    try:
        # Get servers and commands
        servers_info = await mcp_tool.get_available_servers_and_commands()
        
        # Format for frontend
        frontend_servers = {}
        for server_name, info in servers_info.items():
            commands = info.get("commands", [])
            frontend_servers[server_name] = {
                "name": server_name,
                "description": info.get("description", "No description"),
                "commands": commands,
                "hasCommands": len(commands) > 0
            }
        
        return {
            "status": "success",
            "servers": frontend_servers
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc(),
            "servers": {}
        }


@router.get("/mcp/servers/{server_name}/commands", response_model=dict)
async def get_mcp_server_commands(
    server_name: str,
    user: User = Depends(get_current_user),
):
    """
    Get detailed information about commands available for a specific MCP server.
    
    Args:
        server_name: Name of the MCP server
        user: The authenticated user
        
    Returns:
        dict: Detailed information about available commands
    """
    # Get the MCP tool
    mcp_tool = tool_registry.get_tool_by_name("mcp")
    if not mcp_tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP tool not available"
        )
    
    try:
        # Get servers and commands
        servers_info = await mcp_tool.get_available_servers_and_commands()
        
        # Check if server exists
        if server_name not in servers_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP server '{server_name}' not found"
            )
        
        server_info = servers_info[server_name]
        commands = server_info.get("commands", [])
        
        # TODO: In the future, we could add more detailed information about each command
        # such as required parameters, parameter types, etc.
        
        return {
            "status": "success",
            "server": server_name,
            "commands": commands
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting MCP server commands: {str(e)}"
        )
