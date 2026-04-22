"""Rating schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RatingCreate(BaseModel):
    """Rating creation schema"""
    score: float = Field(..., ge=0.0, le=5.0)
    review: Optional[str] = None


class RatingResponse(BaseModel):
    """Rating response schema"""
    id: int
    user_id: int
    movie_id: int
    score: float
    review: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
