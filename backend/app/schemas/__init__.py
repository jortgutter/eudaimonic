"""Pydantic schemas for request/response validation"""
from .movie import MovieCreate, MovieUpdate, MovieResponse
from .user import UserCreate, UserResponse
from .rating import RatingCreate, RatingResponse
from .recommendation import RecommendationResponse, RecommendedMovieResponse
from .chat import ChatRequest, ChatResponse
from .tmdb import TmdbMovieSummary, TmdbSearchResponse, TmdbImportResponse

__all__ = [
    "MovieCreate",
    "MovieUpdate",
    "MovieResponse",
    "UserCreate",
    "UserResponse",
    "RatingCreate",
    "RatingResponse",
    "RecommendationResponse",
    "RecommendedMovieResponse",
    "ChatRequest",
    "ChatResponse",
    "TmdbMovieSummary",
    "TmdbSearchResponse",
    "TmdbImportResponse",
]
