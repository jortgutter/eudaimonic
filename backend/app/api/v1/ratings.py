"""Rating endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db.database import get_db
from app.db.models import Movie, User
from app.schemas import RatingCreate, RatingResponse
from app.services.rating_service import RatingService

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("/users/{user_id}/movies/{movie_id}", response_model=RatingResponse, summary="Create Rating")
def create_rating(
    user_id: int,
    movie_id: int,
    rating_in: RatingCreate,
    db: Session = Depends(get_db),
):
    """Rate a movie for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return RatingService.create_rating(db, user_id, movie_id, rating_in)


@router.get("/users/{user_id}", response_model=list[RatingResponse], summary="List Ratings For User")
def list_user_ratings(
    user_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List ratings for a user."""
    return RatingService.list_ratings_for_user(db, user_id)[:limit]
