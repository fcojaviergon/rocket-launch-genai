import asyncio
import uuid
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING, ClassVar, Union
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from datetime import datetime

# Import AgentService type annotation only for type checking to avoid circular imports
if TYPE_CHECKING:
    from modules.agent.service import AgentService

logger = logging.getLogger(__name__)


class AgentState:
    """
    Class to manage the state of an agent interaction.
    Stores the history of messages, tool calls, and observations.
    """
    
    def __init__(
        self, 
        conversation_id: Optional[uuid.UUID] = None, 
        db: Optional["AsyncSession"] = None,
        agent_service: Optional["AgentService"] = None
    ):
        self.history: List[Dict[str, Any]] = []
        self.conversation_id = conversation_id
        self.db = db
        self.agent_service = agent_service
        
    @classmethod
    async def create(
        cls,
        conversation_id: uuid.UUID,
        db: "AsyncSession",
        agent_service: "AgentService"
    ) -> "AgentState":
        """
        Factory method to create an AgentState with history loaded from the database.
        
        Args:
            conversation_id: ID of the conversation
            db: Database session
            agent_service: Agent service for DB operations
            
        Returns:
            AgentState initialized with conversation history
        """
        # Create new state
        state = cls(conversation_id=conversation_id, db=db, agent_service=agent_service)
        
        # Load existing messages
        await state.load_history()
        
        return state
        
    async def load_history(self) -> None:
        """Load conversation history from the database into the state."""
        if not self.db or not self.agent_service or not self.conversation_id:
            logger.warning("Cannot load history without db, agent_service, and conversation_id")
            return
            
        # Get messages from database
        messages = await self.agent_service.get_messages_by_conversation(
            self.db, self.conversation_id
        )
        
        # Populate agent state with existing messages (without persisting)
        for message in messages:
            if message.role == "user":
                self._add_to_history("user", message.content)
            elif message.role == "assistant":
                self._add_to_history("assistant", message.content)
            elif message.role == "tool":
                # Parse tool messages - format: "Tool Call: tool_name(args)\nResult: result"
                parts = message.content.split("\nResult: ")
                if len(parts) == 2:
                    tool_call = parts[0].replace("Tool Call: ", "")
                    result = parts[1]
                    self._add_action_and_observation_to_history(tool_call, result)
    
    def _add_to_history(self, role: str, content: str) -> None:
        """Add a message to history without persisting to DB."""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
    def _add_action_and_observation_to_history(self, action: str, observation: str) -> None:
        """Add action and observation to history without persisting to DB."""
        self.history.append({
            "role": "tool",
            "content": f"Tool Call: {action}\nResult: {observation}",
            "timestamp": datetime.now().isoformat()
        })
        
    async def add_message(self, role: str, content: str) -> None:
        """
        Add a message to history and persist to database if possible.
        
        Args:
            role: The role of the message sender (user, assistant)
            content: The message content
        """
        # First add to in-memory history
        self._add_to_history(role, content)
        
        # Then persist to DB if possible
        if self.db and self.agent_service and self.conversation_id:
            try:
                await self.agent_service.create_message(
                    self.db, self.conversation_id, role, content
                )
                logger.debug(f"Message from {role} persisted to database")
            except Exception as e:
                logger.error(f"Failed to persist message to database: {e}", exc_info=True)
                # Note: We don't close or rollback the connection here because
                # the connection is managed by the caller (run_agent_loop)
        
    async def add_llm_response(self, content: str) -> None:
        """
        Add a response from the LLM to history and persist to database if possible.
        
        Args:
            content: The LLM response content
        """
        await self.add_message("assistant", content)
        
    async def add_action_and_observation(self, action: str, observation: str) -> None:
        """
        Add a tool call action and its observation to history and persist to database if possible.
        
        Args:
            action: The tool call action
            observation: The observation/result from the tool call
        """
        # First add to in-memory history
        self._add_action_and_observation_to_history(action, observation)
        
        # Then persist to DB if possible
        if self.db and self.agent_service and self.conversation_id:
            try:
                tool_content = f"Tool Call: {action}\nResult: {observation}"
                await self.agent_service.create_message(
                    self.db, self.conversation_id, "tool", tool_content
                )
                logger.debug("Tool call and observation persisted to database")
            except Exception as e:
                logger.error(f"Failed to persist tool call to database: {e}", exc_info=True)
                # Note: We don't close or rollback the connection here because
                # the connection is managed by the caller (run_agent_loop)
        
    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history.
        
        Returns:
            List of message dictionaries
        """
        return self.history
        
    def build_prompt_content(self) -> List[Dict[str, str]]:
        """
        Build the prompt content from history in the format expected by the LLM.
        
        Returns:
            List of message dictionaries in LLM format
        """
        prompt_messages = []
        
        for message in self.history:
            if message["role"] == "user":
                prompt_messages.append({
                    "role": "user",
                    "content": message["content"]
                })
            elif message["role"] == "assistant":
                prompt_messages.append({
                    "role": "assistant", 
                    "content": message["content"]
                })
            elif message["role"] == "tool":
                # Parse tool and observation from format "Tool Call: {action}\nResult: {observation}"
                parts = message["content"].split("\nResult: ")
                if len(parts) == 2:
                    action = parts[0].replace("Tool Call: ", "")
                    observation = parts[1]
                    
                    prompt_messages.append({
                        "role": "assistant",
                        "content": f"I'll use the tool: {action}"
                    })
                    prompt_messages.append({
                        "role": "user",
                        "content": f"Tool result: {observation}"
                    })
                
        return prompt_messages
