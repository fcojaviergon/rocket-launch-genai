from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from core.deps import get_current_active_user, get_current_admin_user, get_db
from database.models.user import User
from modules.auth.service import AuthService
from schemas.auth import UserCreate, UserUpdate, UserResponse, UserListResponse, UserProfileUpdate, UserPasswordUpdate

router = APIRouter()
auth_service = AuthService()

@router.get("", response_model=dict)
async def get_users(
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
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
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "role": current_user.role
    }

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
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
        
        # Update only allowed fields
        restricted_update = UserUpdate(
            email=user_data.email,
            full_name=user_data.full_name
        )
        
        user = await auth_service.update_user(db, current_user.id, restricted_update)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/me/password", response_model=UserResponse)
async def update_current_user_password(
    password_data: UserPasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
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
    
    # Update password
    update_data = UserUpdate(password=password_data.new_password)
    user = await auth_service.update_user(db, current_user.id, update_data)
    return user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
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
    current_user: User = Depends(get_current_admin_user)
):
    """
    Create a new user (admin only)
    """
    try:
        user = await auth_service.register_user(db, user_data)
        # The service already returns a dictionary with the ID as a string
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
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
        
        user = await auth_service.update_user(db, user_id, user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{user_id}", response_model=UserResponse)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
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
