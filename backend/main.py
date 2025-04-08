import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Project imports
from api.v1.api import api_router
from core.config import settings
from database.init_db import init_db
from core.logging_config import configure_logging
from core.middleware.logging_middleware import RequestLoggingMiddleware
from core.middleware.security_middleware import SecurityMiddleware
from core.exceptions import setup_exception_handlers
from core.health import comprehensive_health_check, check_database_connection

# Import handlers to register them (e.g., event handlers or similar)
# TODO: Consider making registration more explicit if possible.
import modules.auth.handlers

# Configure logging using our enhanced logging configuration
logger = configure_logging()

app = FastAPI(
    title="Rocket Launch GenAI Platform API",
    description="API for the Rocket Launch GenAI Platform",
    version="0.1.0"
)

# Setup global exception handlers
setup_exception_handlers(app)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add security middleware with reasonable defaults
# More aggressive rate limiting in production
rate_limit = 60 if settings.ENVIRONMENT == "production" else 200
app.add_middleware(
    SecurityMiddleware,
    rate_limit=rate_limit, 
    time_window=60,
    enable_rate_limiting=True,
    enable_secure_headers=True
)

# Configure CORS for production/development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Event that runs when the application starts."""
    logger.info("Starting application...")
    # Initialize the database and create default users if they don't exist
    try:
        # Ensure necessary directories exist, safely handling potential errors
        try:
            os.makedirs(settings.DOCUMENT_STORAGE_PATH, exist_ok=True)
            logger.info(f"Ensured document storage directory exists: {settings.DOCUMENT_STORAGE_PATH}")
            os.makedirs(settings.LOG_DIR, exist_ok=True)
            logger.info(f"Ensured log directory exists: {settings.LOG_DIR}")
        except OSError as e:
            logger.error(f"Error creating necessary directories: {e}", exc_info=True)
            # Depending on severity, you might want to raise the error or exit
            # raise e 

        await init_db()
        logger.info("Database initialized correctly")
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Rocket Launch GenAI Platform API"}

@app.get("/health")
async def health_check():
    """Simple health check endpoint for monitoring systems"""
    return {"status": "ok"}

@app.get("/health/database")
async def db_health_check():
    """Database-specific health check"""
    result = await check_database_connection()
    return result

@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check of all system components"""
    result = await comprehensive_health_check()
    return result

# Only enable debug endpoints in development mode
if settings.ENVIRONMENT == "development":
    @app.get("/debug/cors")
    async def debug_cors():
        """Endpoint to diagnose CORS issues. Only available in development mode."""
        return {"message": "CORS test successful"}
