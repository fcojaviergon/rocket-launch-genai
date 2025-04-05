import sys
import os
import uvicorn
import logging
from core.config import settings
from core.logging_config import configure_logging

# Add the current directory to the PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Use centralized logging configuration
logger = configure_logging()

if __name__ == "__main__":
    # Disable reload in production for better performance and stability
    reload_mode = False if settings.ENVIRONMENT == 'production' else True
    logger.info(f"Starting server in {settings.ENVIRONMENT} mode")
    uvicorn.run("main:app", host="::", port=8000, reload=reload_mode, log_level="info")
