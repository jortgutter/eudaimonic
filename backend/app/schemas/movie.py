"""Movie schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class MovieBase(BaseModel):
    """Base movie schema"""
    tmdb_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    release_year: Optional[int] = None
    genre: Optional[str] = None
    poster_url: Optional[str] = None
    imdb_id: Optional[str] = None


class MovieCreate(MovieBase):
    """Movie creation schema"""
    pass


class MovieUpdate(BaseModel):
    """Movie update schema"""
    tmdb_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    release_year: Optional[int] = None
    genre: Optional[str] = None
    poster_url: Optional[str] = None


class MovieResponse(MovieBase):
    """Movie response schema"""
    id: int
    tmdb_id: Optional[int] = None
    average_rating: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
