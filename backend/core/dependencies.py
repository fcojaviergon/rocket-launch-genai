# backend/core/dependencies.py
import logging
from typing import Optional, Generator
from functools import lru_cache

# Import Interfaces and Implementations
from core.llm_interface import LLMClientInterface
from core.openai_client import OpenAIClient
from core.anthropic_client import AnthropicClient # Import even if skeleton

# Import Services that need injection or are injected
from services.ai.chat_service import ChatService
from services.ai.completion_service import CompletionService
from modules.document.service import DocumentService
from modules.pipeline.service import PipelineService
from modules.auth.service import AuthService
from modules.pipeline.executor import PipelineExecutor
from modules.agent.service import AgentService
# Import Settings
from core.config import settings

# Import FastAPI dependencies
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

# Import User model and the get_db dependency
from database.models.user import User
from database.session import get_db # Import get_db from its source

logger = logging.getLogger(__name__)

# --- Security & Auth Dependencies (Moved from core/deps.py) ---

# Config OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login") # Use settings
# -------------------------------------------------------------

# --- Singleton Instances --- 
# Use lru_cache(maxsize=None) to create singletons easily for functions with no args

@lru_cache(maxsize=None)
def get_llm_client_instance() -> Optional[LLMClientInterface]:
    """Creates and returns a singleton LLM client instance based on settings."""
    provider = settings.AI_PROVIDER.lower()
    client: Optional[LLMClientInterface] = None
    logger.info(f"Attempting to initialize LLM client for provider: '{provider}'")
    
    if provider == "openai":
        try:
            client = OpenAIClient()
        except Exception as e:
            logger.error(f"Failed to initialize OpenAIClient: {e}", exc_info=True)
            # Decide if we should raise an error or return None
            # Returning None allows app to start but features will fail
    elif provider == "anthropic":
        try:
            client = AnthropicClient()
        except Exception as e:
            logger.error(f"Failed to initialize AnthropicClient: {e}", exc_info=True)
            # Returning None allows app to start but features will fail
    else:
        logger.error(f"Unsupported AI_PROVIDER configured: '{provider}'")
        # Optionally raise ValueError("Invalid AI Provider") if startup should fail
        
    if client:
         logger.info(f"Successfully initialized LLM client for '{provider}'")
    else:
         logger.error(f"LLM Client initialization failed for provider '{provider}'. AI features may not work.")
         
    return client

@lru_cache(maxsize=None)
def get_document_service_instance() -> DocumentService:
    """Creates and returns a singleton DocumentService instance."""
    logger.info("Initializing singleton DocumentService instance...")
    # DocumentService now needs the LLM client
    llm_client = get_llm_client_instance() 
    instance = DocumentService(llm_client=llm_client)
    logger.info("DocumentService singleton initialized.")
    return instance
    
@lru_cache(maxsize=None)
def get_chat_service_instance() -> ChatService:
    """Creates and returns a singleton ChatService instance."""
    logger.info("Initializing singleton ChatService instance...")
    # ChatService needs LLM client and DocumentService
    llm_client = get_llm_client_instance()
    doc_service = get_document_service_instance()
    instance = ChatService(llm_client=llm_client, document_service=doc_service)
    logger.info("ChatService singleton initialized.")
    return instance

@lru_cache(maxsize=None)
def get_pipeline_service_instance() -> PipelineService:
    """Creates and returns a singleton PipelineService instance."""
    logger.info("Initializing singleton PipelineService instance...")
    # PipelineService currently doesn't have complex dependencies in __init__
    instance = PipelineService()
    logger.info("PipelineService singleton initialized.")
    return instance

@lru_cache(maxsize=None)
def get_auth_service_instance() -> AuthService:
    """Creates and returns a singleton AuthService instance."""
    logger.info("Initializing singleton AuthService instance...")
    # AuthService currently doesn't have complex dependencies in __init__
    instance = AuthService()
    logger.info("AuthService singleton initialized.")
    return instance

@lru_cache(maxsize=None)
def get_pipeline_executor_instance() -> PipelineExecutor:
    """Creates and returns a singleton PipelineExecutor instance."""
    logger.info("Initializing singleton PipelineExecutor instance...")
    # PipelineExecutor needs the LLM client
    llm_client = get_llm_client_instance()
    instance = PipelineExecutor(llm_client=llm_client)
    logger.info("PipelineExecutor singleton initialized.")
    return instance

@lru_cache(maxsize=None)
def get_completion_service_instance() -> CompletionService:
    """Creates and returns a singleton CompletionService instance."""
    logger.info("Initializing singleton CompletionService instance...")
    llm_client = get_llm_client_instance()
    # Add handling if llm_client is None, maybe raise error or return a dummy?
    # For now, assume it succeeds or raises within get_llm_client_instance if fatal
    if llm_client is None:
        # Option 1: Raise error to prevent app start without LLM
        raise RuntimeError("LLM Client could not be initialized. CompletionService cannot start.")
        # Option 2: Log error and return None or a dummy service (if applicable)
        # logger.error("LLM Client is None, CompletionService may not function.")
        # return None # Or a dummy service instance
    instance = CompletionService(llm_client=llm_client)
    logger.info("CompletionService singleton initialized.")
    return instance

@lru_cache(maxsize=None)
def get_agent_service_instance() -> AgentService:
    """Creates and returns a singleton AgentService instance."""
    logger.info("Initializing singleton AgentService instance...")
    
    # Create the service instance - AgentService no longer takes arguments in __init__
    instance = AgentService()
    logger.info("AgentService singleton initialized.")
    return instance

# --- FastAPI Dependency Functions --- 
# These functions simply call the singleton instance getters

def get_llm_client() -> Optional[LLMClientInterface]:
    return get_llm_client_instance()

def get_document_service() -> DocumentService:
    return get_document_service_instance()

def get_chat_service() -> ChatService:
    return get_chat_service_instance()

def get_pipeline_service() -> PipelineService:
    return get_pipeline_service_instance()

def get_auth_service() -> AuthService:
    return get_auth_service_instance()

def get_pipeline_executor() -> PipelineExecutor:
    return get_pipeline_executor_instance()

def get_completion_service() -> CompletionService:
    return get_completion_service_instance()


def get_agent_service() -> AgentService:
    return get_agent_service_instance()


# Note: The get_db dependency still likely resides in core/deps.py or similar
# as it manages session lifecycle per request, not a singleton service. # <-- This is now incorrect, get_db is imported above

# --- User Dependency Functions (Moved from core/deps.py) ---

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dependency to get the current user from the JWT token
    
    Args:
        db: Asynchronous database session
        token: JWT token
        
    Returns:
        User: Authenticated user
        
    Raises:
        HTTPException: If credentials are invalid or user does not exist
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Debug logging can be helpful but might expose token details if not careful
        # logger.debug(f"Attempting to decode token: {token[:10]}...")
        
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM] # Use settings
        )
        
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            logger.warning("Token payload does not contain 'sub' field")
            raise credentials_exception
            
        # Convert user_id to UUID
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            logger.warning(f"Could not convert user_id '{user_id_str}' to UUID.")
            raise credentials_exception
            
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.warning(f"Unexpected error when decoding token: {e}")
        raise credentials_exception
        
    # Search user in the database
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"User with ID {user_id} not found in database")
        raise credentials_exception
        
    # No need to check is_active here, handled by get_current_active_user if needed
    # logger.debug(f"User {user.email} (ID: {user_id}) authenticated successfully")
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get the current active user
    
    Args:
        current_user: Current user
        
    Returns:
        User: Active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user {current_user.id} attempted access.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user), # Depends on active user
) -> User:
    """
    Dependency to get the current user with admin role
    
    Args:
        current_user: Current user
        
    Returns:
        User: Admin user
        
    Raises:
        HTTPException: If user is not admin or inactive
    """
    # get_current_active_user already checks for active status
    if current_user.role != "admin":
        logger.warning(f"User {current_user.id} lacks admin privileges for requested action.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have sufficient permissions to perform this action"
        )
    return current_user

# Note: The get_db dependency still likely resides in core/deps.py or similar
# as it manages session lifecycle per request, not a singleton service. 