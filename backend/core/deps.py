from typing import Generator, Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import logging

from core.config import settings
from database.session import get_db
from database.models.user import User


logger = logging.getLogger(__name__)
# Set logger level to DEBUG to see all log messages
logger.setLevel(logging.DEBUG)

# Config OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dependency to get the current user from the JWT token
    
    Args:
        db: Asynchronous database session
        token: JWT token
        
    Returns:
        User: Authenticated user
        
    Raises:
        HTTPException: If credentials are invalid or user does not exist
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        logger.debug(f"Attempting to decode token: {token[:10]}...")
        logger.debug(f"Using SECRET_KEY: {settings.SECRET_KEY[:5]}...")
        logger.debug(f"Using algorithm: HS256")
        
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        logger.debug(f"Token decoded successfully!")
        logger.debug(f"Token payload: {payload}")

        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token payload does not contain 'sub' field")
            raise credentials_exception
            
        # Convert user_id to UUID
        try:
            user_id = UUID(user_id)
            logger.debug(f"Parsed user_id as UUID: {user_id}")
        except ValueError as e:
            logger.warning(f"Could not convert user_id to UUID: {str(e)}")
            raise credentials_exception
            
    except JWTError as e:
        logger.warning(f"JWT decode error: {str(e)}")
        # Log more details about the token to help debug
        try:
            # Try to decode without verification to see payload structure
            #unverified_payload = jwt.decode(token, options={"verify_signature": False})
            unverified_payload = jwt.decode(token, 'dummy_key', options={"verify_signature": False})

            logger.warning(f"Unverified token payload: {unverified_payload}")
            
            # Check if alg matches what we expect
            header = jwt.get_unverified_header(token)
            logger.warning(f"Token header: {header}")
            
            if header.get('alg') != 'HS256':
                logger.warning(f"Token algorithm mismatch: expected HS256, got {header.get('alg')}")
                
        except Exception as decode_error:
            logger.warning(f"Could not decode token even without verification: {str(decode_error)}")
            
        logger.warning(f"First 20 chars of token: {token[:20]}...")
        raise credentials_exception
    except Exception as e:
        logger.warning(f"Unexpected error when decoding token: {str(e)}")
        raise credentials_exception
        
    # Search user in the database
    logger.debug(f"Looking up user with ID {user_id} in database")
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"User with ID {user_id} not found in database")
        raise credentials_exception
    if not user.is_active:
        logger.warning(f"User with ID {user_id} is inactive")
        raise HTTPException(status_code=400, detail="Inactive user")
        
    logger.debug(f"User {user.email} (ID: {user_id}) authenticated successfully")
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get the current active user
    
    Args:
        current_user: Current user
        
    Returns:
        User: Active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get the current user with admin role
    
    Args:
        current_user: Current user
        
    Returns:
        User: Admin user
        
    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have sufficient permissions to perform this action"
        )
    return current_user
