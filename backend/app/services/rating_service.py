"""Rating business logic"""
from sqlmodel import Session

from app.db.models import Rating
from app.schemas import RatingCreate
from app.services.movie_service import MovieService


class RatingService:
    """Service for rating operations"""

    @staticmethod
    def create_rating(db: Session, user_id: int, movie_id: int, rating_in: RatingCreate) -> Rating:
        """Create or update a rating and refresh movie average rating."""
        existing = (
            db.query(Rating)
            .filter(Rating.user_id == user_id, Rating.movie_id == movie_id)
            .first()
        )

        if existing:
            existing.score = rating_in.score
            existing.review = rating_in.review
            db.commit()
            db.refresh(existing)
            MovieService.update_average_rating(db, movie_id)
            return existing

        rating = Rating(
            user_id=user_id,
            movie_id=movie_id,
            score=rating_in.score,
            review=rating_in.review,
        )
        db.add(rating)
        db.commit()
        db.refresh(rating)
        MovieService.update_average_rating(db, movie_id)
        return rating

    @staticmethod
    def list_ratings_for_user(db: Session, user_id: int) -> list[Rating]:
        """Return all ratings for a user."""
        return db.query(Rating).filter(Rating.user_id == user_id).order_by(Rating.created_at.desc()).all()
