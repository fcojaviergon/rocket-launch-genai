"""
Settings for the database session
"""
from typing import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    async_scoped_session,
)
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import asyncio
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

# Configuración para sesiones síncronas (para tareas Celery)
sync_db_url = settings.get_sync_database_url()

# Create synchronous engine with optimized configuration
sync_engine = create_engine(
    sync_db_url,
    echo=settings.DB_ECHO_LOG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create synchronous session factory
SyncSessionFactory = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

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
    Uses the global AsyncSessionFactory for consistency.
    """
    # Simply create session from the global factory
    session: AsyncSession = AsyncSessionFactory() 
    
    logger.debug(f"Session {id(session)} created via factory.")
    
    try:
        yield session # 1. Provide the session
        # 2. If the 'yield' is exited without exceptions, make a commit:
        await session.commit() 
        logger.debug(f"Session {id(session)} committed via factory.")
    except Exception as e:
        logger.error(f"Session {id(session)} rollback due to error: {e}", exc_info=True)
        # 3. If an exception occurs within the 'with', make a rollback:
        await session.rollback() 
        raise # 4. Re-raise the exception
    finally:
        # 5. Close the session at the end (always):
        # Only close the session, do NOT dispose the engine.
        # Disposing the engine closes the entire connection pool.
        await session.close()
        logger.debug(f"Session {id(session)} closed via factory.")

# Funciones síncronas para tareas Celery
def get_sync_db() -> Generator[Session, None, None]:
    """
    Get a synchronous database session for Celery tasks
    
    Returns:
        Generator[Session, None, None]: Synchronous database session
    """
    session = SyncSessionFactory()
    try:
        yield session
    finally:
        session.close()

@contextmanager
def get_sync_session_context() -> Generator[Session, None, None]:
    """
    Context manager to provide a synchronous database session.
    Uses the global SyncSessionFactory for consistency.
    """
    # Create session from the global factory
    session: Session = SyncSessionFactory()
    
    logger.debug(f"Sync session {id(session)} created via factory.")
    
    try:
        yield session # 1. Provide the session
        # 2. If the 'yield' is exited without exceptions, make a commit:
        session.commit()
        logger.debug(f"Sync session {id(session)} committed via factory.")
    except Exception as e:
        logger.error(f"Sync session {id(session)} rollback due to error: {e}", exc_info=True)
        # 3. If an exception occurs within the 'with', make a rollback:
        session.rollback()
        raise # 4. Re-raise the exception
    finally:
        # 5. Close the session at the end (always):
        session.close()
        logger.debug(f"Sync session {id(session)} closed via factory.")
