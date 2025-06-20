from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
import uuid

class UserBase(BaseModel):
    """Base schema for users"""
    email: EmailStr
    full_name: str
    role: Optional[str] = "user"
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    """Schema to create users"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema to update users"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserProfileUpdate(BaseModel):
    """Schema to update user profile"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserPasswordUpdate(BaseModel):
    """Schema to update password"""
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """Schema for user responses"""
    id: uuid.UUID

    class Config:
        from_attributes = True


class UserListResponse(UserResponse):
    """Schema to list users with additional information"""
    created_at: datetime
    role: str


class PaginatedUserResponse(BaseModel):
    """Schema for paginated list of users"""
    items: List[UserListResponse] # Use UserListResponse for items
    total: int
    page: int
    page_size: int
    pages: int


class Token(BaseModel):
    """Schema for authentication token"""
    access_token: str
    refresh_token: str
    token_type: str
    user: dict


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str

class UserResponseWithRole(UserResponse):
    """Schema for user responses with role"""
    role: str
