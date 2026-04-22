"""Tests for API endpoints"""
import pytest


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data


def test_create_movie(client):
    """Test movie creation"""
    movie_data = {
        "title": "Inception",
        "description": "A sci-fi thriller",
        "release_year": 2010,
        "genre": "Sci-Fi,Thriller",
        "imdb_id": "tt1375666",
    }
    response = client.post("/api/v1/movies/", json=movie_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Inception"
    assert data["id"] is not None


def test_list_movies(client):
    """Test listing movies"""
    # Create a movie first
    movie_data = {
        "title": "The Matrix",
        "release_year": 1999,
        "genre": "Sci-Fi",
    }
    client.post("/api/v1/movies/", json=movie_data)
    
    # Test listing
    response = client.get("/api/v1/movies/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


def test_get_movie(client):
    """Test getting a specific movie"""
    # Create a movie first
    movie_data = {
        "title": "Pulp Fiction",
        "release_year": 1994,
    }
    create_response = client.post("/api/v1/movies/", json=movie_data)
    movie_id = create_response.json()["id"]
    
    # Get the movie
    response = client.get(f"/api/v1/movies/{movie_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Pulp Fiction"


def test_search_movies(client):
    """Test searching movies"""
    # Create movies
    movies = [
        {"title": "Inception", "genre": "Sci-Fi"},
        {"title": "Interstellar", "genre": "Sci-Fi,Drama"},
        {"title": "The Dark Knight", "genre": "Action,Crime"},
    ]
    for movie in movies:
        client.post("/api/v1/movies/", json=movie)
    
    # Search for sci-fi
    response = client.get("/api/v1/movies/search?q=Sci-Fi")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


def test_update_movie(client):
    """Test updating a movie"""
    # Create a movie
    movie_data = {"title": "Avatar", "release_year": 2009}
    create_response = client.post("/api/v1/movies/", json=movie_data)
    movie_id = create_response.json()["id"]
    
    # Update it
    update_data = {"title": "Avatar: The Way of Water", "release_year": 2022}
    response = client.put(f"/api/v1/movies/{movie_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Avatar: The Way of Water"


def test_delete_movie(client):
    """Test deleting a movie"""
    # Create a movie
    movie_data = {"title": "Titanic"}
    create_response = client.post("/api/v1/movies/", json=movie_data)
    movie_id = create_response.json()["id"]
    
    # Delete it
    response = client.delete(f"/api/v1/movies/{movie_id}")
    assert response.status_code == 200
    
    # Verify it's gone
    get_response = client.get(f"/api/v1/movies/{movie_id}")
    assert get_response.status_code == 404
