"""User schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user schema"""
    username: str
    email: EmailStr


class UserCreate(UserBase):
    """User creation schema"""
    password: str


class UserResponse(UserBase):
    """User response schema"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
