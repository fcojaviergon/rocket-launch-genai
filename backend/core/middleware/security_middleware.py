from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

from core.logging_config import get_logger
from core.config import settings

logger = get_logger("app.security")

class RateLimiter:
    """
    Simple in-memory rate limiter implementation
    
    For production, consider using Redis for distributed rate limiting
    """
    
    def __init__(self, rate_limit: int = 100, time_window: int = 60):
        """
        Initialize rate limiter
        
        Args:
            rate_limit: Maximum requests per time window
            time_window: Time window in seconds
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.blocked_ips: Dict[str, datetime] = {}
        
    def is_rate_limited(self, ip: str) -> bool:
        """
        Check if the IP is currently rate limited
        
        Args:
            ip: IP address to check
            
        Returns:
            bool: True if rate limited, False otherwise
        """
        # Clear expired blocks
        current_time = datetime.now()
        expired_blocks = [ip for ip, expires_at in self.blocked_ips.items() 
                         if current_time > expires_at]
        for ip in expired_blocks:
            del self.blocked_ips[ip]
        
        # Check if IP is blocked
        if ip in self.blocked_ips:
            return True
            
        # Get current time
        now = time.time()
        
        # Remove requests outside the time window
        self.requests[ip] = [req_time for req_time in self.requests[ip] 
                           if now - req_time <= self.time_window]
        
        # Check if rate limited
        if len(self.requests[ip]) >= self.rate_limit:
            # Block for 5 minutes on abuse
            self.blocked_ips[ip] = datetime.now() + timedelta(minutes=5)
            logger.warning(f"IP {ip} blocked for rate limit abuse", 
                         extra={"security": {"ip": ip, "reason": "rate_limit_abuse"}})
            return True
            
        # Add current request
        self.requests[ip].append(now)
        return False

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers and rate limiting
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        rate_limit: int = 100,
        time_window: int = 60,
        enable_rate_limiting: bool = True,
        enable_secure_headers: bool = True
    ):
        super().__init__(app)
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_secure_headers = enable_secure_headers
        self.rate_limiter = RateLimiter(rate_limit, time_window)
        
    async def dispatch(self, request: Request, call_next: callable) -> Response:
        # Get client IP
        client_host = request.client.host if request.client else "unknown"
        
        # Rate limiting
        if self.enable_rate_limiting and client_host != "unknown":
            # Skip rate limiting for local development
            if not (client_host == "127.0.0.1" or client_host == "::1" or 
                   client_host.startswith("192.168.") or 
                   client_host.startswith("10.") or
                   settings.ENVIRONMENT == "development"):
                
                # Check rate limit
                if self.rate_limiter.is_rate_limited(client_host):
                    logger.warning(f"Rate limit exceeded for IP {client_host}", 
                               extra={"security": {"ip": client_host, "reason": "rate_limit_exceeded"}})
                    
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests. Please try again later."}
                    )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        if self.enable_secure_headers:
            # Common security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            
            # Only add security headers in production
            if settings.ENVIRONMENT == "production":
                # Use a Content Security Policy in production
                # This is a basic policy, customize based on your needs
                response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
                
                # HTTP Strict Transport Security (force HTTPS)
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                
                # Permissions Policy (formerly Feature Policy)
                response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                
        return response 