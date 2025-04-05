"""
Utilidades de base de datos para las tareas asíncronas
"""
import logging
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from core.config import settings
import re

# Set logger
logger = logging.getLogger("tasks.database")

# Get database connection URL
def get_database_url():
    """Get the database connection URL in synchronous format"""
    try:
        # Get the URL from settings
        url = settings.get_sync_database_url()
        # Ensure it doesn't have the asyncpg driver
        if "+asyncpg" in url:
            url = url.replace("+asyncpg", "")
        # Log the URL (sanitized)
        sanitized_url = re.sub(r':[^@]+@', ':***@', url)
        logger.info(f"Base de datos sincrona URL: {sanitized_url}")
        return url
    except Exception as e:
        logger.error(f"Error obteniendo URL de base de datos: {e}")
        # Fallback to a standard URL in case of error
        return "postgresql://rocket:rocket123@localhost:5432/rocket_launch_genai"

# Try to create engine with error handling
try:
    # Get URL and sanitize it for logging
    db_url = get_database_url()
    sanitized_url = re.sub(r':[^@]+@', ':***@', db_url)
    logger.info(f"Creating engine with URL: {sanitized_url}")
    
    # Create synchronous engine and session
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(engine)
    logger.info("Engine and SessionLocal created successfully")
except Exception as e:
    logger.error(f"Error al crear engine: {e}")
    # Set engine and SessionLocal to None to avoid import errors
    # (will allow modules to load but will fail when trying to use them)
    engine = None
    SessionLocal = None
    raise

def update_pipeline_execution_status(execution_id, status, results=None, error_message=None):
    """
    Update the status of a pipeline execution in the database.
    Uses direct SQL to avoid import model issues.
    
    Args:
        execution_id: ID of the execution to update
        status: New status (PENDING, RUNNING, COMPLETED, FAILED, CANCELED)
        results: Execution results (for COMPLETED)
        error_message: Error message (for FAILED)
    
    Returns:
        bool: True if the update was successful, False otherwise
    """
    if not execution_id:
        logger.error("No execution ID provided")
        return False
    
    # Validate that we have engine and SessionLocal
    if engine is None or SessionLocal is None:
        logger.error("Failed to initialize database connection")
        return False
    
    try:
        # Create dictionary with values to update
        update_values = {
            "status": status,
            "updated_at": datetime.now()
        }
        
        # Add fields based on the status
        if status == "COMPLETED":
            update_values["completed_at"] = datetime.now()
            if results:
                # Convert results to JSON
                if isinstance(results, dict):
                    update_values["results"] = json.dumps(results)
                else:
                    update_values["results"] = results
        
        if status == "FAILED" and error_message:
            update_values["error_message"] = error_message
        
        if status == "RUNNING" and "started_at" not in update_values:
            update_values["started_at"] = datetime.now()
        
        # Build SQL to update the execution
        with SessionLocal() as session:
            # Determine which fields to update
            set_clause_parts = []
            params = {"execution_id": execution_id}
            
            for key, value in update_values.items():
                params[key] = value
                set_clause_parts.append(f"{key} = :{key}")
            
            set_clause = ", ".join(set_clause_parts)
            
            # Execute SQL
            sql = text(f"UPDATE pipeline_executions SET {set_clause} WHERE id = :execution_id")
            result = session.execute(sql, params)
            session.commit()
            
            affected_rows = result.rowcount
            logger.info(f"Update execution {execution_id} to status {status}: {affected_rows} rows affected")
            return affected_rows > 0
    
    except Exception as e:
        logger.error(f"Error updating execution {execution_id}: {e}")
        return False 