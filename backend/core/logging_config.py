import logging
import logging.handlers
import os
import json
import time
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Union

from core.config import settings

class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging in production environments.
    Makes logs easier to parse by log aggregation tools like ELK, Graylog, etc.
    """
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        # Add extra contextual info if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
            
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
            
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(record.extra)
            
        return json.dumps(log_data)

class ContextAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds contextual information to log records.
    Allows adding request_id, user_id, and other contextual info to logs.
    """
    def process(self, msg, kwargs):
        # Ensure extra is a dict
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
            
        # Add context from the adapter
        if hasattr(self, 'request_id'):
            kwargs['extra']['request_id'] = self.request_id
            
        if hasattr(self, 'user_id'):
            kwargs['extra']['user_id'] = self.user_id
            
        return msg, kwargs

def get_logger(name: str, request_id: Optional[str] = None, user_id: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with contextual information attached.
    
    Args:
        name: The name of the logger (usually __name__)
        request_id: Optional request ID for request tracking
        user_id: Optional user ID for user tracking
        
    Returns:
        A configured logger with contextual information
    """
    logger = logging.getLogger(name)
    adapter = ContextAdapter(logger, {})
    
    if request_id:
        adapter.request_id = request_id
        
    if user_id:
        adapter.user_id = user_id
        
    return adapter

def configure_logging() -> logging.Logger:
    """
    Configure logging for the application
    
    Sets up logging based on environment (development vs production):
    - In development: Human-readable format with DEBUG level, logs to console.
    - In production: JSON structured logs with INFO level, logs to rotating files.
    
    Returns:
        A configured root application logger
    """
    log_level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO
    
    # Create log directory structure
    log_dir = Path(settings.LOG_DIR)
    access_log_path = log_dir / "access.log"
    error_log_path = log_dir / "errors.log"
    app_log_path = log_dir / "app.log"
    security_log_path = log_dir / "security.log"
    
    # Create directory if it doesn't exist
    try:
        log_dir.mkdir(exist_ok=True, parents=True)
    except OSError as e:
        # Use basicConfig for fallback logging if directory creation fails
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Failed to create log directory {log_dir}: {e}")
        # Potentially raise the error or exit if logging to file is critical
        # For now, we'll proceed, but file logging might not work
    
    # Configure root logger
    if settings.ENVIRONMENT == "development":
        # Human-readable format for development, logs to console
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        
        # Configure basic logging (handles root logger and console output)
        logging.basicConfig(
            level=log_level,
            format=log_format,
            datefmt=date_format,
        )
        # Root logger configured, app_logger will propagate to it by default
    else:
        # JSON format for production (better for log analysis)
        
        # Configure root logger to only use our JSON handler (e.g., for console)
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Remove existing handlers attached by basicConfig or libraries
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add our JSON formatter StreamHandler (for console/stdout)
        json_console_handler = logging.StreamHandler()
        json_console_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(json_console_handler)
    
    # Reduce verbosity of external libraries in production
    if settings.ENVIRONMENT == "production":
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("celery").setLevel(logging.INFO)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    # Create app logger
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    
    # In development, let app logs propagate to the root logger (console)
    # In production, file handlers are attached, so no need to propagate to root's console handler
    app_logger.propagate = settings.ENVIRONMENT == "development"
    
    # Configure handlers based on environment
    if settings.ENVIRONMENT == "production":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "%Y-%m-%d %H:%M:%S"
        )
    
    # Error log handler (rotated, 10MB max size, keep 5 backups)
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_path,
        maxBytes=10485760,  # 10MB
        backupCount=5,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    app_logger.addHandler(error_handler)
    
    # Application log handler (all levels)
    app_handler = logging.handlers.RotatingFileHandler(
        app_log_path,
        maxBytes=10485760,  # 10MB
        backupCount=5,
    )
    app_handler.setLevel(log_level)
    app_handler.setFormatter(formatter)
    app_logger.addHandler(app_handler)
    
    # Add security logger for auth events
    security_logger = logging.getLogger("app.security")
    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False
    
    security_handler = logging.handlers.RotatingFileHandler(
        security_log_path,
        maxBytes=10485760,  # 10MB
        backupCount=5,
    )
    security_handler.setLevel(logging.INFO)
    security_handler.setFormatter(formatter)
    security_logger.addHandler(security_handler)
    
    # Add access logger for request/response logging
    access_logger = logging.getLogger("app.access")
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False
    
    access_handler = logging.handlers.RotatingFileHandler(
        filename=access_log_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8' # Specify encoding
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(formatter)
    access_logger.addHandler(access_handler)
    
    # Console handler for all app logs in development
    if settings.ENVIRONMENT == "development":
        # No need for a separate console handler on app_logger
        # Logs will propagate to the root logger which has a console handler via basicConfig
        pass
    
    logging.info(f"Logging configured for {settings.ENVIRONMENT} environment")
    return app_logger 