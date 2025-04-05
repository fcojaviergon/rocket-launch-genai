"""
Settings for the database session
"""
from typing import AsyncGenerator
from contextlib import asynccontextmanager
import re

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    async_scoped_session,
)
from sqlalchemy.pool import NullPool
from sqlalchemy import event
import asyncio
import greenlet
import logging

from core.config import settings

logger = logging.getLogger(__name__)

# Specific configurations for asyncpg
pool_options = {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# Obtener la URL correcta desde settings
connection_url = settings.get_async_database_url()
logger.info(f"Using database connection URL (sanitized): {connection_url.replace(str(settings.POSTGRES_PASSWORD), '***')}")

# Create the async engine with optimized configuration
async_engine = create_async_engine(
    connection_url,
    echo=settings.DB_ECHO_LOG,
    future=True,
    **pool_options
)

# Create the async session factory
AsyncSessionFactory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create the async session factory with specific scope per greenlet
AsyncSessionLocal = AsyncSessionFactory

# To diagnose connection issues
if settings.DB_ECHO_LOG:
    @event.listens_for(async_engine.sync_engine, "connect")
    def _on_connect(dbapi_connection, connection_record):
        logger.info("New database connection established")

    @event.listens_for(async_engine.sync_engine, "checkout")
    def _on_checkout(dbapi_connection, connection_record, connection_proxy):
        logger.info("Database connection checked out from pool")

    @event.listens_for(async_engine.sync_engine, "checkin")
    def _on_checkin(dbapi_connection, connection_record):
        logger.info("Database connection returned to pool")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get an asynchronous database session.
    
    This function is mainly used as a dependency in FastAPI.
    For use in contexts where you don't have access to FastAPI Depends,
    consider using AsyncSessionLocal directly.
    
    Returns:
        AsyncGenerator[AsyncSession, None]: Asynchronous database session.
    """
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()

@asynccontextmanager
async def get_async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager to provide an asynchronous database session.
    
    This context manager ensures proper event loop handling and connection management
    for tasks running in different execution contexts (like Celery workers).
    """
    # Get the current event loop - this ensures we're using the loop from the current context
    loop = asyncio.get_event_loop()
    logger.debug(f"Creating session in event loop {id(loop)}")
    
    # Create a session specific to this event loop
    session: AsyncSession = AsyncSessionFactory()
    logger.debug(f"Session {id(session)} created in loop {id(loop)}.")
    
    try:
        yield session # 1. Provide the session
        # 2. If the 'yield' is exited without exceptions, make a commit:
        await session.commit() 
        logger.debug(f"Session {id(session)} committed in loop {id(loop)}.")
    except Exception as e:
        logger.error(f"Session {id(session)} rollback due to error: {e}", exc_info=True)
        # 3. If an exception occurs within the 'with', make a rollback:
        await session.rollback() 
        raise # 4. Re-raise the exception
    finally:
        # 5. Close the session at the end (always):
        try:
            # Properly close the session
            await session.close()
            
            # Get the raw connection from the session if available
            # This ensures underlying connections are properly released
            if hasattr(session, 'bind') and session.bind is not None:
                engine = session.bind
                if hasattr(engine, 'dispose'):
                    await engine.dispose()
                    
            logger.debug(f"Session {id(session)} closed in loop {id(loop)}.")
        except Exception as close_error:
            logger.error(f"Error closing session {id(session)}: {close_error}", exc_info=True)
