from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from uuid import UUID

from core.config import settings
from database.models.user import User
from core.events.bus import event_bus
from modules.auth.events import UserRegisteredEvent
from core.security import (
    verify_password,
    get_password_hash,
    create_access_token as create_jwt_token,
    create_refresh_token as create_jwt_refresh_token,
)
from fastapi import HTTPException, status
from jose import jwt, JWTError, ExpiredSignatureError
import logging
# Import custom exceptions (assuming they are in exceptions.py)
from .exceptions import (
    AuthError,
    InvalidCredentialsError,
    UserNotFoundError,
    UserInactiveError,
    EmailAlreadyExistsError,
    InvalidTokenError,
    TokenExpiredError
)

# Setup logger for this service
logger = logging.getLogger(__name__)

class AuthService:
    """Authentication service"""
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return verify_password(plain_password, hashed_password)
        
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return get_password_hash(password)
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email"""
        logger.debug(f"Looking for user with email: {email}")
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        user = result.scalars().first()
        logger.debug(f"User found for email {email}: {user is not None}")
        return user
    
    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate user"""
        logger.info(f"Attempting authentication for user: {email}")
        user = await self.get_user_by_email(db, email)
        if not user:
            logger.warning(f"Authentication failed: User not found for email {email}")
            raise InvalidCredentialsError("Incorrect email or password")
            
        password_valid = self.verify_password(password, user.hashed_password)
        logger.debug(f"Password verification result for {email}: {password_valid}")
        
        if not password_valid:
            logger.warning(f"Authentication failed: Invalid password for user {email}")
            raise InvalidCredentialsError("Incorrect email or password")
        
        # Check if user is active (except superadmin who can always access)
        if not user.is_active and user.role != "superadmin":
            logger.warning(f"Authentication failed: User {email} is inactive")
            raise UserInactiveError("User account is inactive")
            
        logger.info(f"Authentication successful for user: {email}")
        return user
    
    async def register_user(self, db: AsyncSession, user_data):
        """Register a new user"""
        existing_user = await self.get_user_by_email(db, user_data.email)
        if existing_user:
            logger.warning(f"Registration failed: Email {user_data.email} already exists.")
            raise EmailAlreadyExistsError("Email already registered")
            
        hashed_password = self.get_password_hash(user_data.password)
        
        user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            is_active=True if not hasattr(user_data, 'is_active') or user_data.is_active is None else user_data.is_active,
            role=user_data.role if hasattr(user_data, 'role') and user_data.role else "user"
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Publish user registered event
        await event_bus.publish(UserRegisteredEvent(
            user_id=str(user.id),
            email=user.email,
            name=user.full_name
        ))
        
        # Return the ORM User object
        logger.info(f"User {user.email} registered successfully with ID {user.id}")
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        return create_jwt_token(data["sub"], expires_delta)
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        return create_jwt_refresh_token(data["sub"])
    
    async def verify_refresh_token(self, db: AsyncSession, token: str) -> User:
        """Decodes refresh token, validates payload, and returns the active user."""
        try:
            # Decode using jose.jwt directly
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"] 
            )
            user_id = payload.get("sub")
            token_type = payload.get("type")

            if not user_id:
                logger.error("Refresh token payload missing 'sub' (user_id).")
                raise InvalidTokenError("Invalid token payload (no user_id)")

            # Convert user_id string from token payload to UUID
            try:
                user_uuid = UUID(user_id)
            except ValueError:
                logger.error(f"Invalid user_id format in refresh token payload: {user_id}")
                raise InvalidTokenError("Invalid user_id format in token")

            if token_type != "refresh":
                logger.error(f"Invalid token type received, expected 'refresh', got '{token_type}'.")
                raise InvalidTokenError("Invalid token type (not a refresh token)")

            logger.info(f"Refresh token signature verified for user_id: {user_id}")
            user = await db.get(User, user_uuid)

            if not user:
                logger.error(f"User specified in refresh token not found: {user_id}")
                raise UserNotFoundError("User from token not found")

            if not user.is_active:
                logger.warning(f"Attempt to refresh token for inactive user: {user_id}")
                raise UserInactiveError("User account is inactive")

            logger.info(f"User verified for token refresh: {user.email}, Role: {user.role}")
            return user

        except ExpiredSignatureError:
            logger.warning("Expired refresh token presented.")
            raise TokenExpiredError("Refresh token has expired")
        except JWTError as e:
            logger.warning(f"Invalid refresh token received: {e}")
            raise InvalidTokenError(f"Invalid refresh token: {e}")
        except HTTPException:
             # Re-raise HTTPExceptions if they were somehow raised internally (shouldn't happen now)
             raise
        except Exception as e:
            logger.exception(f"Unexpected error during refresh token verification: {e}")
            # Raise a generic auth error
            raise AuthError(f"An unexpected error occurred during token verification: {e}")
        
    async def get_users(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
        """Get list of users"""
        query = select(User).offset(skip).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        return users # Return list of ORM objects
        
    async def get_users_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 10, search: str = None) -> tuple[List[User], int]:
        """Get paginated list of users with total and optional search"""
        # Base query
        query = select(User)
        count_query = select(func.count()).select_from(User)
        
        # Apply search filter if exists
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            query = query.where(
                (User.full_name.ilike(search_term)) | 
                (User.email.ilike(search_term))
            )
            count_query = count_query.where(
                (User.full_name.ilike(search_term)) | 
                (User.email.ilike(search_term))
            )
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute queries
        result = await db.execute(query)
        users = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return users, total # Return list of ORM objects and total count
    
    async def get_user(self, db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        user = await db.get(User, user_id)
        if not user:
            return None # Return None if not found
        return user # Return ORM object
        
    async def update_user(self, db: AsyncSession, user_id: UUID, user_data):
        """Update user"""
        # Get original user from database
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        db_user = result.scalars().first()
        
        if not db_user:
            return None
            
        # Permission checks for superadmin modification should ideally happen in the API layer
        # before calling this service method, based on the retrieved user and the current user.

        # Prepare data for update
        update_data = {}
        if user_data.email is not None:
            # Verify that the email does not exist for another user
            if user_data.email != db_user.email:
                existing_user = await self.get_user_by_email(db, user_data.email)
                if existing_user and str(existing_user.id) != str(user_id):
                    raise ValueError("Email already registered for another user")
            update_data["email"] = user_data.email
            
        if user_data.full_name is not None:
            update_data["full_name"] = user_data.full_name
            
        if user_data.password is not None and user_data.password.strip():
            update_data["hashed_password"] = self.get_password_hash(user_data.password)
            
        if user_data.role is not None:
            update_data["role"] = user_data.role
            
        if user_data.is_active is not None:
            update_data["is_active"] = user_data.is_active
            
        if update_data:
            stmt = update(User).where(User.id == user_id).values(**update_data)
            await db.execute(stmt)
            await db.commit()
            
            # Get updated user
            query = select(User).where(User.id == user_id)
            result = await db.execute(query)
            updated_user = result.scalars().first()
            
            # Return the updated ORM User object
            return updated_user
        
        # If there are no changes, return the current data
        return db_user # Return the original ORM User object
        
    async def delete_user(self, db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Delete user"""
        # Get original user from database
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        db_user = result.scalars().first()
        
        if not db_user:
            return None # Return None if not found
            
        # Delete user
        await db.delete(db_user) # Use session delete
        await db.commit()
        
        # Return the ORM object of the user that was deleted
        return db_user
