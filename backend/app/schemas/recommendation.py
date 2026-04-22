"""Recommendation schemas"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .movie import MovieResponse


class RecommendationResponse(BaseModel):
    """Recommendation response schema"""
    id: int
    user_id: int
    movie_id: int
    score: float
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendedMovieResponse(BaseModel):
    """Recommendation with movie details"""

    recommendation: RecommendationResponse
    movie: MovieResponse
