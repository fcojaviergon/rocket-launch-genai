import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.logging_config import get_logger

logger = get_logger("app.access")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    
    This middleware:
    1. Generates a unique request ID for each request
    2. Logs the incoming request with details
    3. Measures request processing time
    4. Logs the outgoing response with status code and timing
    5. Adds the request ID to response headers
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Get request details
        path = request.url.path
        method = request.method
        client_host = request.client.host if request.client else "unknown"
        
        # Create request-specific logger with request ID
        req_logger = get_logger("app.access", request_id=request_id)
        
        # Log the request
        req_logger.info(
            f"Request received: {method} {path}",
            extra={
                "http": {
                    "method": method,
                    "path": path,
                    "client_ip": client_host,
                    "query_params": str(request.query_params),
                    "headers": dict(request.headers.items()),
                }
            }
        )
        
        # Process request and track timing
        start_time = time.time()
        
        try:
            # Add request_id to request state for access in route handlers
            request.state.request_id = request_id
            
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log the response
            req_logger.info(
                f"Response sent: {response.status_code} in {process_time:.3f}s",
                extra={
                    "http": {
                        "status_code": response.status_code,
                        "processing_time": process_time,
                        "headers": dict(response.headers.items()),
                    }
                }
            )
            
            return response
            
        except Exception as e:
            # Calculate processing time even for errors
            process_time = time.time() - start_time
            
            # Log the error
            req_logger.error(
                f"Request failed: {str(e)}",
                exc_info=True,
                extra={
                    "http": {
                        "processing_time": process_time,
                        "error": str(e),
                    }
                }
            )
            
            # Re-raise the exception to be handled by exception handlers
            raise 