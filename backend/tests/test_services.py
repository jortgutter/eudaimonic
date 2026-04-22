"""Tests for business logic services"""
import pytest
from app.services.movie_service import MovieService
from app.schemas import MovieCreate


def test_create_movie_service(db):
    """Test creating a movie via service"""
    movie_data = MovieCreate(
        title="Gladiator",
        release_year=2000,
        genre="Action,Drama",
    )
    movie = MovieService.create_movie(db, movie_data)
    assert movie.id is not None
    assert movie.title == "Gladiator"


def test_get_movie_service(db):
    """Test retrieving a movie via service"""
    movie_data = MovieCreate(title="The Godfather", release_year=1972)
    movie = MovieService.create_movie(db, movie_data)
    
    retrieved = MovieService.get_movie(db, movie.id)
    assert retrieved is not None
    assert retrieved.title == "The Godfather"


def test_search_movies_service(db):
    """Test searching movies via service"""
    movies = [
        MovieCreate(title="Forrest Gump", genre="Drama,Romance"),
        MovieCreate(title="Forrest Run", genre="Action"),
    ]
    for m in movies:
        MovieService.create_movie(db, m)
    
    results = MovieService.search_movies(db, "Forrest")
    assert len(results) == 2
