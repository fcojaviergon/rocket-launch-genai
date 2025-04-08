from pydantic import PostgresDsn, field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Dict, Any, List, Union, ClassVar
import secrets
import os
import re
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # API configuration
    API_V1_STR: str = "/api/v1"
   
    # Config for env file loading
    # Pydantic-settings will automatically load from .env and environment variables
    # Defaulting to .env.local, but overrideable via ENV_FILE environment variable
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env.local"), # Allow overriding env file via ENV_FILE
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Security
    SECRET_KEY: str = os.environ.get("SECRET_KEY", secrets.token_urlsafe(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    JWT_ALGORITHM: str = "HS256" # Algorithm for JWT
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    
    # Environment
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")

    # Database
    POSTGRES_USER: str = os.environ.get("POSTGRES_USER", "rocket")
    POSTGRES_PASSWORD: str = os.environ.get("POSTGRES_PASSWORD", "rocket123")
    POSTGRES_HOST: str = os.environ.get("POSTGRES_HOST", "localhost")
    POSTGRES_DB: str = os.environ.get("POSTGRES_DB", "rocket_launch_genai")
    DATABASE_URL: Optional[PostgresDsn] = None
    DB_ECHO_LOG: bool = os.environ.get("DB_ECHO_LOG", "false").lower() == "true"
    
    # CORS - Default to empty list, populated based on environment later
    BACKEND_CORS_ORIGINS: List[str] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            # Handle comma-separated string from env var
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        # Allow empty list if nothing is provided
        elif v is None:
            return []
        raise ValueError(f"Invalid format for BACKEND_CORS_ORIGINS: {v}")
    
    # Redis configuration
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    
    # Celery configuration
    CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    CELERY_WORKER_CONCURRENCY: int = int(os.environ.get("CELERY_WORKER_CONCURRENCY", 4))
    CELERY_WORKER_POOL: str = os.environ.get("CELERY_WORKER_POOL", "prefork")
    
    # External services / AI Provider Configuration
    AI_PROVIDER: str = os.environ.get("AI_PROVIDER", "openai").lower()
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: Optional[str] = os.environ.get("ANTHROPIC_API_KEY", None)
   
    # Default models (can be overridden)
    DEFAULT_CHAT_MODEL: str = os.environ.get("DEFAULT_CHAT_MODEL", "gpt-4")
    DEFAULT_EMBEDDING_MODEL: str = os.environ.get("DEFAULT_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Document storage
    # Calculate path relative to the project root for local development default
    _local_project_root: ClassVar[str] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _default_local_storage_path: ClassVar[str] = os.path.join(_local_project_root, "backend", "storage", "documents")
    # Use env var for Docker override, default to calculated local path
    DOCUMENT_STORAGE_PATH: str = os.environ.get("CONTAINER_DOCUMENT_STORAGE_PATH", _default_local_storage_path)

    # Logging
    _default_local_log_path: ClassVar[str] = os.path.join(_local_project_root, "backend", "logs")
    # Use env var for Docker override, default to calculated local path
    LOG_DIR: str = os.environ.get("CONTAINER_LOG_DIR", _default_local_log_path)

    # Initial Admin User (for init_db)
    # These should be set in the environment for initial setup
    INITIAL_ADMIN_EMAIL: str = "admin@example.com" # Default for convenience, override recommended
    INITIAL_ADMIN_PASSWORD: str # MUST be set in environment

    # --- Custom Validators ---

    @field_validator('AI_PROVIDER')
    def check_ai_provider(cls, v):
        provider = v.lower()
        if provider not in ['openai', 'anthropic']:
            raise ValueError(f"Unsupported AI_PROVIDER: '{v}'. Must be 'openai' or 'anthropic'.")
        return provider

    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info) -> Any:
        # If DATABASE_URL is explicitly set in the environment, use it
        if isinstance(v, str) and v:
             # Ensure it uses asyncpg driver if provided directly
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            return v

        # Otherwise, build it from components
        values = info.data
        if not all(k in values for k in ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_DB"]):
             raise ValueError("Database connection details (USER, PASSWORD, HOST, DB) must be provided via environment variables if DATABASE_URL is not set.")

        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST"),
            path=f"/{values.get('POSTGRES_DB')}",
        )
    
    # Simplified methods for database URLs
    def get_async_database_url(self) -> str:
        """Returns the validated async database connection URL."""
        if not self.DATABASE_URL:
            # This should not happen if validation passed, but defensive check
            raise ValueError("DATABASE_URL is not configured.")
        # Pydantic validation ensures it's a valid DSN
        # Our validator ensures it starts with postgresql+asyncpg://
        return str(self.DATABASE_URL)

    def get_sync_database_url(self) -> str:
        """Returns the database connection URL for synchronous operations (e.g., Alembic)."""
        async_url = self.get_async_database_url()
        # Simply replace the asyncpg driver part
        sync_url = async_url.replace("+asyncpg", "", 1)
        return sync_url
    
    # Initialize and log settings after validation
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Set default CORS origins based on environment if not provided
        # This logic runs after initial validation and loading from env vars
        if not self.BACKEND_CORS_ORIGINS:
            if self.ENVIRONMENT == "development":
                self.BACKEND_CORS_ORIGINS = [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    "http://localhost", # Allow access from host machine if frontend runs there
                    "http://127.0.0.1",
                ]
                logger.info(f"Default development CORS origins set: {self.BACKEND_CORS_ORIGINS}")
            elif self.ENVIRONMENT == "production":
                 # In production, origins MUST be explicitly configured via env var
                 logger.warning("BACKEND_CORS_ORIGINS is not set in production environment. No origins will be allowed.")
                 self.BACKEND_CORS_ORIGINS = [] # Ensure it's an empty list
            else:
                 logger.info(f"No default CORS origins for environment: {self.ENVIRONMENT}")
                 self.BACKEND_CORS_ORIGINS = [] # Ensure it's an empty list

        # Logging important configurations (avoid logging sensitive info directly)
        logger.info(f"Environment: {self.ENVIRONMENT}")
        logger.info(f"Debug logging for DB: {self.DB_ECHO_LOG}")
        logger.info(f"Document storage path: {self.DOCUMENT_STORAGE_PATH}")
        logger.info(f"CORS Origins: {self.BACKEND_CORS_ORIGINS}")

        # Sanitize sensitive info for logging
        if self.SECRET_KEY:
            logger.info(f"SECRET_KEY is set (starts with: {self.SECRET_KEY[:5]}...).")
        else:
            # This should raise an error during validation now, but added defensively
            logger.error("CRITICAL: SECRET_KEY is not set!")

        if self.POSTGRES_PASSWORD:
             logger.info(f"POSTGRES_PASSWORD is set.") # Don't log any part of it
        else:
             logger.error("CRITICAL: POSTGRES_PASSWORD is not set!")

        if self.OPENAI_API_KEY:
            logger.info(f"OPENAI_API_KEY is set (starts with: {self.OPENAI_API_KEY[:5]}...).")
        else:
            logger.warning("OPENAI_API_KEY is not set or empty.")

        # Log database URLs (sanitized)
        try:
            async_url = self.get_async_database_url()
            sync_url = self.get_sync_database_url()
            # Basic sanitization: remove password
            sanitized_async_url = re.sub(r':([^:]+)@', ':***@', async_url)
            sanitized_sync_url = re.sub(r':([^:]+)@', ':***@', sync_url)
            logger.info(f"Async DB URL: {sanitized_async_url}")
            logger.info(f"Sync DB URL: {sanitized_sync_url}")
        except ValueError as e:
            logger.error(f"Failed to get database URLs: {e}")

# Export settings as a singleton instance
try:
    settings = Settings()
except ValidationError as e:
    logger.critical(f"CRITICAL ERROR: Failed to load application settings: {e}")
    # Optionally re-raise or exit if settings are critical for startup
    raise e
