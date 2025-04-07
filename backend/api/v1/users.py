from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from uuid import UUID

from core.dependencies import get_current_active_user, get_current_admin_user, get_db
from database.models.user import User
from database.models.document import Document
from modules.auth.service import AuthService
from schemas.auth import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, 
    UserProfileUpdate, UserPasswordUpdate, UserResponseWithRole
)
from core.dependencies import (
    get_auth_service, get_db, get_current_user, 
    get_current_active_user, get_current_admin_user
)

router = APIRouter()

@router.get("", response_model=dict)
async def get_users(
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Get paginated list of users (admin only)
    """
    skip = (page - 1) * page_size
    users, total = await auth_service.get_users_paginated(db, skip=skip, limit=page_size, search=search)
    
    return {
        "items": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }

@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user
    """
    return {
        current_user
    }

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update current user data
    """
    try:
        # Check if email is already registered by another user
        if user_data.email and user_data.email != current_user.email:
            existing_user = await auth_service.get_user_by_email(db, user_data.email)
            if existing_user and str(existing_user.id) != str(current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email is already registered"
                )
        
        # Create UserUpdate schema instance from UserProfileUpdate for the service call
        update_payload = UserUpdate(
            email=user_data.email if user_data.email is not None else ..., # Use Pydantic ellipsis for optional unset
            full_name=user_data.full_name if user_data.full_name is not None else ...
        )
        
        # Service now returns the User ORM object
        updated_user = await auth_service.update_user(db, current_user.id, update_payload)
        if not updated_user:
             # Should not happen if current_user exists, but defensive check
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found during update")
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/me/password", response_model=UserResponse)
async def update_current_user_password(
    password_data: UserPasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update current user password
    """
    # Verify that the current password is correct
    is_valid = auth_service.verify_password(
        password_data.current_password, 
        current_user.hashed_password
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Create UserUpdate schema instance for the service call
    update_payload = UserUpdate(password=password_data.new_password)
    
    # Service returns the User ORM object
    updated_user = await auth_service.update_user(db, current_user.id, update_payload)
    if not updated_user:
         # Should not happen, defensive check
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found during password update")
    return updated_user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Get a user by ID (admin only)
    """
    user = await auth_service.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends()
):
    """
    Create a new user (admin only)
    """
    try:
        user = await auth_service.register_user(db, user_data)
        # The service already returns a dictionary with the ID as a string
        # Service now returns the ORM object, Pydantic handles conversion
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    auth_service: AuthService = Depends()
):
    """
    Update a user (admin only)
    """
    try:
        # Check if the user to update exists
        existing_user = await auth_service.get_user(db, user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Special rules for superadmin
        if existing_user["role"] == "superadmin" and current_user.role != "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Only a superadmin can modify another superadmin"
            )
        
        # Do not allow changing role to superadmin unless user is a superadmin
        if user_data.role == "superadmin" and current_user.role != "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Only a superadmin can assign the superadmin role"
            )
        
        # Service returns User ORM object
        user = await auth_service.update_user(db, user_id, user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{user_id}", response_model=UserResponse)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    auth_service: AuthService = Depends()
):
    """
    Delete a user (admin only)
    """
    # Verify that user is not deleting themselves
    if str(user_id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own user"
        )
    
    user = await auth_service.delete_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
