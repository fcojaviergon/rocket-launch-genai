import asyncio
import logging
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import async_engine as engine, AsyncSessionLocal as SessionLocal
# Import all models to ensure SQLAlchemy registers them
from database.models import BaseModel, User, Document, DocumentEmbedding, DocumentProcessingResult, Conversation, Message, Pipeline
from modules.auth.service import AuthService
# Import settings
from core.config import settings

# Logging configuration
logger = logging.getLogger(__name__)

async def create_tables(connection) -> None:
    """Create all database tables if they don't exist"""
    logger.info("Creating database tables...")
    await connection.run_sync(BaseModel.metadata.create_all)
    logger.info("Database tables created successfully")

async def create_admin_user(db: AsyncSession) -> User:
    """Create an admin user if it doesn't exist"""
    # Check if admin user already exists
    logger.info(f"Checking for admin user with email: {settings.INITIAL_ADMIN_EMAIL}")
    query = select(User).where(User.email == settings.INITIAL_ADMIN_EMAIL)
    result = await db.execute(query)
    admin_user = result.scalars().first()
    
    if admin_user:
        # Check if admin user has the correct role
        if admin_user.role != "admin":
            logger.warning(f"Existing user {settings.INITIAL_ADMIN_EMAIL} found, updating role to admin.")
            admin_user.role = "admin" # Ensure role is admin
            admin_user.is_superuser = True # Ensure superuser status
            admin_user.is_active = True # Ensure active status
            await db.commit()
            logger.info("Admin role updated for existing user")
        else:
            logger.info("Admin user already exists")
        return admin_user
    
    # Create admin user
    logger.info(f"Creating initial admin user: {settings.INITIAL_ADMIN_EMAIL}")
    if not settings.INITIAL_ADMIN_PASSWORD:
        logger.error("INITIAL_ADMIN_PASSWORD is not set in settings. Cannot create admin user.")
        raise ValueError("Initial admin password must be set in environment variables.")

    auth_service = AuthService()
    admin_user = User(
        email=settings.INITIAL_ADMIN_EMAIL,
        hashed_password=auth_service.get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
        full_name="Admin User",
        is_superuser=True,
        role="admin",
        is_active=True
    )
    
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)
    
    logger.info("Admin user created successfully")
    return admin_user

async def create_default_pipeline_config(db: AsyncSession, admin_user: User) -> None:
    """Create a default pipeline configuration"""
    # Check if configuration already exists
    query = select(Pipeline).where(Pipeline.name == "Basic Processing")
    result = await db.execute(query)
    default_pipeline = result.scalars().first()
    
    if default_pipeline:
        logger.info("Default pipeline already exists")
        return
    
    # Create default pipeline
    default_pipeline = Pipeline(
        name="Basic Processing",
        description="Basic pipeline for document processing",
        type="document",
        steps=[
            {
                "name": "text_extraction",
                "config": {"format": "plain"}
            },
            {
                "name": "summarizer", 
                "config": {"max_tokens": 200}
            },
            {
                "name": "keyword_extraction",
                "config": {"max_keywords": 10}
            }
        ],
        config_metadata={
            "icon": "document",
            "color": "blue"
        },
        user_id=admin_user.id
    )
    
    db.add(default_pipeline)
    await db.commit()
    logger.info("Default pipeline created successfully")

async def init_db():
    """Initialize the database with tables and default data"""
    logger.info("Starting database initialization...")

    # Then create all tables
    async with engine.begin() as conn:
        await create_tables(conn)
    
    # Create a session
    async with SessionLocal() as db:
        # Create admin user
        admin_user = await create_admin_user(db)
        
        # Create default pipeline
        await create_default_pipeline_config(db, admin_user)
    
    logger.info("Database initialization completed")

# Function to run asynchronous initialization
def run_init():
    logger.info("Running database initialization...")
    asyncio.run(init_db())
    logger.info("Database initialization complete")

if __name__ == "__main__":
    # Configure basic logging when run as a script
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    run_init()
