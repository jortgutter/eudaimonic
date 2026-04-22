"""TMDb schemas"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TmdbMovieSummary(BaseModel):
    """TMDb search result payload"""

    id: int
    title: str
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: float = 0.0
    popularity: float = 0.0
    genre_ids: list[int] = Field(default_factory=list)


class TmdbSearchResponse(BaseModel):
    """TMDb search response wrapper"""

    page: int
    total_results: int
    total_pages: int
    results: list[TmdbMovieSummary]


class TmdbImportResponse(BaseModel):
    """TMDb import response"""

    id: int
    tmdb_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    release_year: Optional[int] = None
    genre: Optional[str] = None
    poster_url: Optional[str] = None
    imdb_id: Optional[str] = None
    average_rating: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
