from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
from pydantic import ValidationError
import json

from core.logging_config import get_logger
from core.config import settings
from core.serialization import UUIDEncoder

logger = get_logger("app.exceptions")

class AppException(Exception):
    """Base application exception with status code and detail"""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

def setup_exception_handlers(app: FastAPI):
    """Configure global exception handlers for the application"""
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle standard HTTP exceptions"""
        # Get request ID if available
        request_id = getattr(request.state, "request_id", None)
        exception_logger = get_logger("app.exceptions", request_id=request_id)
        
        # Log the exception
        exception_logger.warning(
            f"HTTP exception: {exc.status_code} - {exc.detail}",
            extra={"http": {"status_code": exc.status_code, "path": request.url.path}}
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors with detailed information"""
        # Get request ID if available
        request_id = getattr(request.state, "request_id", None)
        exception_logger = get_logger("app.exceptions", request_id=request_id)
        
        # Extract the error details
        error_details = exc.errors()
        readable_errors = []
        
        for error in error_details:
            location = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            readable_errors.append(f"{location}: {message}")
        
        # Log the validation error
        exception_logger.warning(
            f"Validation error for {request.method} {request.url.path}",
            extra={
                "validation_errors": error_details,
                "http": {"path": request.url.path, "method": request.method}
            }
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation error",
                "errors": readable_errors
            }
        )
    
    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
        """Handle Pydantic validation errors"""
        # Get request ID if available
        request_id = getattr(request.state, "request_id", None)
        exception_logger = get_logger("app.exceptions", request_id=request_id)
        
        # Log the validation error
        exception_logger.warning(
            f"Pydantic validation error for {request.method} {request.url.path}",
            extra={
                "validation_errors": exc.errors(),
                "http": {"path": request.url.path, "method": request.method}
            }
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Data validation error",
                "errors": exc.errors()
            }
        )
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle application-specific exceptions"""
        # Get request ID if available
        request_id = getattr(request.state, "request_id", None) 
        exception_logger = get_logger("app.exceptions", request_id=request_id)
        
        # Log the application exception
        exception_logger.error(
            f"Application exception: {exc.status_code} - {exc.detail}",
            extra={"http": {"status_code": exc.status_code, "path": request.url.path}}
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Handle any unhandled exceptions"""
        # Get request ID if available
        request_id = getattr(request.state, "request_id", None)
        exception_logger = get_logger("app.exceptions", request_id=request_id)
        
        # Get the full stack trace
        tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
        
        # Log the unhandled exception with full stack trace
        exception_logger.error(
            f"Unhandled exception: {str(exc)}",
            exc_info=True,
            extra={
                "http": {
                    "path": request.url.path, 
                    "method": request.method
                },
                "traceback": tb
            }
        )
        
        # In production, don't return the actual error message
        if settings.ENVIRONMENT == "production":
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
        
        # In development, return more details
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "message": str(exc),
                "traceback": tb
            }
        ) 