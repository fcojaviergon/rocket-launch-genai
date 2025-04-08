from pydantic import BaseModel, EmailStr, Field, UUID4, field_serializer
from typing import Optional
from datetime import datetime
from uuid import UUID

# Shared properties
class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    role: str
    created_at: datetime
    updated_at: datetime

# Properties to return to client
class UserResponse(UserBase):
    id: UUID

    @field_serializer('id')
    def serialize_id(self, v: UUID, _info):
        return str(v)

    class Config:
        from_attributes = True

# Properties to receive on user creation
class UserCreate(UserBase):
    password: str

# Properties to receive on user update
class UserUpdate(UserBase):
    password: Optional[str] = None

# Properties to return on user deletion
class UserDelete(BaseModel):
    email: EmailStr
    is_active: bool
    is_superuser: bool
    role: str
    created_at: datetime
    updated_at: datetime 