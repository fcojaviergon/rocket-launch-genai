from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from uuid import UUID

from core.config import settings
from database.models.user import User
from core.events.bus import event_bus
from modules.auth.events import UserRegisteredEvent
from core.security import verify_password, get_password_hash, create_access_token as create_jwt_token, create_refresh_token as create_jwt_refresh_token

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
        print(f"Looking for user with email: {email}")
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        user = result.scalars().first()
        print(f"User found: {user is not None}")
        return user
    
    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate user"""
        print(f"Authenticating user: {email}")
        user = await self.get_user_by_email(db, email)
        if not user:
            print(f"User not found: {email}")
            return None
            
        password_valid = self.verify_password(password, user.hashed_password)
        print(f"Password verification: {password_valid}")
        
        if not password_valid:
            print(f"Invalid password for user: {email}")
            return None
        
        # Check if user is active (except superadmin who can always access)
        if not user.is_active and user.role != "superadmin":
            print(f"Inactive user: {email}")
            return None
            
        print(f"Authentication successful for: {email}")
        return user
    
    async def register_user(self, db: AsyncSession, user_data):
        """Register a new user"""
        # Check if email already exists
        existing_user = await self.get_user_by_email(db, user_data.email)
        if existing_user:
            raise ValueError("Email already registered")
            
        # Create password hash
        hashed_password = self.get_password_hash(user_data.password)
        
        # Create user
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
        
        # Return a dictionary with ID as string
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "role": user.role,
            "created_at": user.created_at
        }
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        return create_jwt_token(data["sub"], expires_delta)
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        return create_jwt_refresh_token(data["sub"])
        
    async def get_users(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[dict]:
        """Get list of users"""
        query = select(User).offset(skip).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        
        # Convert UUIDs to strings to avoid validation errors
        user_list = []
        for user in users:
            user_dict = {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "role": user.role,
                "created_at": user.created_at
            }
            user_list.append(user_dict)
            
        return user_list
        
    async def get_users_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 10, search: str = None) -> tuple[List[dict], int]:
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
        
        # Convert to list of dictionaries with ID as string
        user_list = []
        for user in users:
            user_dict = {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "role": user.role,
                "created_at": user.created_at
            }
            user_list.append(user_dict)
        
        return user_list, total
    
    async def get_user(self, db: AsyncSession, user_id: UUID) -> Optional[dict]:
        """Get user by ID"""
        user = await db.get(User, user_id)
        if not user:
            return None
            
        # Convert UUID to string
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "role": user.role
        }
        
    async def update_user(self, db: AsyncSession, user_id: UUID, user_data):
        """Update user"""
        # Get original user from database
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        db_user = result.scalars().first()
        
        if not db_user:
            return None
            
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
            
            # Return dictionary with updated data
            return {
                "id": str(updated_user.id),
                "email": updated_user.email,
                "full_name": updated_user.full_name,
                "is_active": updated_user.is_active,
                "role": updated_user.role
            }
        
        # If there are no changes, return the current data
        return {
            "id": str(db_user.id),
            "email": db_user.email,
            "full_name": db_user.full_name,
            "is_active": db_user.is_active,
            "role": db_user.role
        }
        
    async def delete_user(self, db: AsyncSession, user_id: UUID) -> Optional[dict]:
        """Delete user"""
        # Get original user from database
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        db_user = result.scalars().first()
        
        if not db_user:
            return None
            
        # Save user data before deleting
        user_data = {
            "id": str(db_user.id),
            "email": db_user.email,
            "full_name": db_user.full_name,
            "is_active": db_user.is_active,
            "role": db_user.role
        }
        
        # Delete user
        stmt = delete(User).where(User.id == user_id)
        await db.execute(stmt)
        await db.commit()
        
        # Return deleted user data
        return user_data
