"""Movie endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db.database import get_db
from app.schemas import MovieCreate, MovieResponse, MovieUpdate
from app.services.movie_service import MovieService

router = APIRouter(prefix="/movies", tags=["movies"])


@router.post("", response_model=MovieResponse, summary="Create Movie")
def create_movie(movie_in: MovieCreate, db: Session = Depends(get_db)):
    """Create a new movie"""
    return MovieService.create_movie(db, movie_in)


@router.get("", response_model=list[MovieResponse], summary="List Movies")
def list_movies(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get paginated list of movies"""
    return MovieService.get_all_movies(db, skip=skip, limit=limit)


@router.get("/search", response_model=list[MovieResponse], summary="Search Movies")
def search_movies(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search movies by title or genre"""
    return MovieService.search_movies(db, query=q, skip=skip, limit=limit)


@router.get("/{movie_id}", response_model=MovieResponse, summary="Get Movie")
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    """Get movie by ID"""
    movie = MovieService.get_movie(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.put("/{movie_id}", response_model=MovieResponse, summary="Update Movie")
def update_movie(
    movie_id: int,
    movie_update: MovieUpdate,
    db: Session = Depends(get_db),
):
    """Update movie details"""
    movie = MovieService.update_movie(db, movie_id, movie_update)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.delete("/{movie_id}", summary="Delete Movie")
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    """Delete a movie"""
    if not MovieService.delete_movie(db, movie_id):
        raise HTTPException(status_code=404, detail="Movie not found")
    return {"message": "Movie deleted successfully"}
