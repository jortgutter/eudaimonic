"""SQLModel ORM models"""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

class MovieBase(SQLModel):
    """Common movie fields."""

    tmdb_id: Optional[int] = Field(default=None, index=True)
    title: str = Field(index=True, nullable=False)
    description: Optional[str] = Field(default=None)
    release_year: Optional[int] = Field(default=None)
    genre: Optional[str] = Field(default=None)
    poster_url: Optional[str] = Field(default=None)
    imdb_id: Optional[str] = Field(default=None, index=True, unique=True)
    average_rating: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Movie(MovieBase, table=True):
    """Movie model"""

    __tablename__ = "movies"

    id: Optional[int] = Field(default=None, primary_key=True)
