"""Schemas for the local movie catalog database."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

    
class MovieCatalogItem(BaseModel):
    """Movie record from the local SQLite catalog."""

    id: int
    title: str
    summary: Optional[str] = None
    image_url: Optional[str] = None
    vote_average: Optional[float] = None
    release_date: Optional[date] = None
    adult: bool = False
    genres: list[str] = Field(default_factory=list)
    Wisdom: float
    Courage: float
    Humanity: float
    Justice: float
    Temperance: float
    Transcendence: float


class WatchProviderItem(BaseModel):
    """Distinct watch provider for a region."""

    provider_id: int
    provider_name: str


class VirtueScoreSet(BaseModel):
    """Virtue scores indexed for a movie."""

    wisdom: Optional[float] = None
    courage: Optional[float] = None
    humanity: Optional[float] = None
    justice: Optional[float] = None
    temperance: Optional[float] = None
    transcendence: Optional[float] = None


class MovieVirtueScoresResponse(BaseModel):
    """Movie record with virtue scores."""

    movie: MovieCatalogItem
    virtue_scores: VirtueScoreSet