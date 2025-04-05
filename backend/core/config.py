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
   
    # Config for env file loading - simplified
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    print(f"Environment file path: {model_config['env_file']}")
    print(f"Environment file encoding: {model_config['env_file_encoding']}")

    # Security
    SECRET_KEY: str = os.environ.get("SECRET_KEY", secrets.token_urlsafe(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
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
    
    # CORS - Allow from frontend in local dev and specific domains in production
    BACKEND_CORS_ORIGINS: List[str] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Redis configuration
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    
    # Celery configuration
    CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    CELERY_WORKER_CONCURRENCY: int = int(os.environ.get("CELERY_WORKER_CONCURRENCY", 4))
    CELERY_WORKER_POOL: str = os.environ.get("CELERY_WORKER_POOL", "prefork")
    
    # External services
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_API_BASE_URL: Optional[str] = os.environ.get("OPENAI_API_BASE_URL", None)
    
    # Document storage
    DOCUMENT_STORAGE_PATH: str = os.environ.get(
        "DOCUMENT_STORAGE_PATH", 
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "documents")
    )

    print(f"DOCUMENT_STORAGE_PATH: {DOCUMENT_STORAGE_PATH}")

    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info) -> Any:
        if v:
            if isinstance(v, str) and not v.startswith("postgresql+asyncpg://"):
                print("WARN: DATABASE_URL provided but might not use asyncpg driver.")
            return v

        values = info.data
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST", "localhost"),
            path=f"/{values.get('POSTGRES_DB', 'rocket')}",
        )
    
    # Nuevos métodos para URLs de base de datos
    def get_async_database_url(self) -> str:
        """
        Returns the database connection URL for SQLAlchemy AsyncEngine,
        correcting format issues with slashes.
        """
        # Convert to string if it's a PostgresDsn object
        db_url = str(self.DATABASE_URL)
        
        # Asegurarse de que sea una URL AsyncPG
        if not "+asyncpg" in db_url:
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            else:
                db_url = f"postgresql+asyncpg://{db_url}"
        
        db_url = re.sub(r'(@[^/]+)//([^/]+)', r'\1/\2', db_url)
        
        return db_url
    
    def get_sync_database_url(self) -> str:
        """
        Returns the database connection URL for SQLAlchemy Engine,
        correcting format issues with slashes and removing the asyncpg driver.
        """
        # Get the base URL and correct format issues
        db_url = self.get_async_database_url()
        
        # Convert to synchronous format
        if "+asyncpg" in db_url:
            db_url = db_url.replace("+asyncpg", "")
        
        return db_url
    
    # Initialize default CORS origins based on environment
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set default CORS origins if not provided
        if not self.BACKEND_CORS_ORIGINS:
            if self.ENVIRONMENT == "development":
                self.BACKEND_CORS_ORIGINS = [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    "http://localhost",
                    "http://127.0.0.1",
                ]
            else:
                # In production, should be configured via env vars
                self.BACKEND_CORS_ORIGINS = []
        
        # Ensure document storage path exists
        os.makedirs(self.DOCUMENT_STORAGE_PATH, exist_ok=True)
        
        # Print important configuration details during startup
        print(f"Environment: {self.ENVIRONMENT}")
        
        # Sanitize sensitive info for logging
        if self.SECRET_KEY:
            print(f"Using SECRET_KEY starting with: {self.SECRET_KEY[:5]}...")
        
        if self.OPENAI_API_KEY:
            print(f"Using OPENAI_API_KEY starting with: {self.OPENAI_API_KEY[:5]}...")
        else:
            print("WARNING: OPENAI_API_KEY is not set or empty!")

        # Log database URLs (sanitized)
        async_url = self.get_async_database_url()
        sync_url = self.get_sync_database_url()
        print(f"Async DB URL: {re.sub(r':[^@]+@', ':***@', async_url)}")
        print(f"Sync DB URL: {re.sub(r':[^@]+@', ':***@', sync_url)}")


# Export settings as a singleton
settings = Settings()
