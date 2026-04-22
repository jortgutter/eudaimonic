"""SQLModel ORM models"""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class UserBase(SQLModel):
    """Common user fields."""

    username: str = Field(index=True, nullable=False)
    email: str = Field(index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(UserBase, table=True):
    """User model"""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)

    ratings: list["Rating"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    recommendations: list["Recommendation"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


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

    ratings: list["Rating"] = Relationship(
        back_populates="movie",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    recommendations: list["Recommendation"] = Relationship(
        back_populates="movie",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class RatingBase(SQLModel):
    """Common rating fields."""

    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    movie_id: int = Field(foreign_key="movies.id", index=True, nullable=False)
    score: float = Field(nullable=False)
    review: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Rating(RatingBase, table=True):
    """User movie rating model"""

    __tablename__ = "ratings"

    id: Optional[int] = Field(default=None, primary_key=True)

    user: Optional[User] = Relationship(back_populates="ratings")
    movie: Optional[Movie] = Relationship(back_populates="ratings")


class RecommendationBase(SQLModel):
    """Common recommendation fields."""

    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    movie_id: int = Field(foreign_key="movies.id", index=True, nullable=False)
    score: float = Field(nullable=False)
    reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Recommendation(RecommendationBase, table=True):
    """Movie recommendation model"""

    __tablename__ = "recommendations"

    id: Optional[int] = Field(default=None, primary_key=True)

    user: Optional[User] = Relationship(back_populates="recommendations")
    movie: Optional[Movie] = Relationship(back_populates="recommendations")
