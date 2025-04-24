"""
Settings for the database session
"""
from typing import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
import logging

from core.config import settings

logger = logging.getLogger(__name__)

# Obtener la URL correcta desde settings
connection_url = settings.get_async_database_url()
logger.info(f"Using database connection URL (sanitized): {connection_url.replace(str(settings.POSTGRES_PASSWORD), '***')}")

# Specific configurations for asyncpg
pool_options = {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

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

# Configuración del motor síncrono para Celery
sync_engine = create_engine(
    settings.get_sync_database_url(),
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DB_ECHO_LOG
)

# Crear la factoría de sesiones síncronas
SyncSessionFactory = sessionmaker(
    sync_engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Función para obtener una sesión síncrona para Celery
def get_celery_db_session() -> Session:
    """
    Crea y devuelve una sesión síncrona de base de datos para usar en tareas Celery.
    Esta función devuelve directamente una sesión, no un contexto ni un generador.
    
    Returns:
        Session: Una sesión de base de datos síncrona lista para usar en Celery
    """
    return SyncSessionFactory()

# Context manager para sesiones síncronas (para Celery)
@contextmanager
def get_sync_session_context() -> Generator[Session, None, None]:
    """
    Context manager para proporcionar una sesión síncrona de base de datos.
    Principalmente para uso en tareas Celery.
    
    Yields:
        Session: Una sesión de base de datos síncrona
    """
    session = SyncSessionFactory()
    
    logger.debug(f"Sync session {id(session)} created via factory.")
    
    try:
        yield session
        session.commit()
        logger.debug(f"Sync session {id(session)} committed via factory.")
    except Exception as e:
        logger.error(f"Sync session {id(session)} rollback due to error: {e}", exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()
        logger.debug(f"Sync session {id(session)} closed via factory.")