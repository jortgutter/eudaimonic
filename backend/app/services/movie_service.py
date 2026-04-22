"""Movie business logic"""
from sqlmodel import Session

from app.db.models import Movie, Rating
from app.schemas import MovieCreate, MovieUpdate


class MovieService:
    """Service for movie operations"""

    @staticmethod
    def create_movie(db: Session, movie_in: MovieCreate) -> Movie:
        """Create a new movie"""
        movie = Movie(**movie_in.model_dump())
        db.add(movie)
        db.commit()
        db.refresh(movie)
        return movie

    @staticmethod
    def get_movie(db: Session, movie_id: int) -> Movie | None:
        """Get movie by ID"""
        return db.query(Movie).filter(Movie.id == movie_id).first()

    @staticmethod
    def get_all_movies(db: Session, skip: int = 0, limit: int = 10) -> list[Movie]:
        """Get paginated list of movies"""
        return db.query(Movie).offset(skip).limit(limit).all()

    @staticmethod
    def update_movie(
        db: Session, movie_id: int, movie_update: MovieUpdate
    ) -> Movie | None:
        """Update movie"""
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            return None
        for key, value in movie_update.model_dump(exclude_unset=True).items():
            setattr(movie, key, value)
        db.commit()
        db.refresh(movie)
        return movie

    @staticmethod
    def delete_movie(db: Session, movie_id: int) -> bool:
        """Delete movie"""
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            return False
        db.delete(movie)
        db.commit()
        return True

    @staticmethod
    def search_movies(db: Session, query: str, skip: int = 0, limit: int = 10) -> list[Movie]:
        """Search movies by title or genre"""
        return (
            db.query(Movie)
            .filter(
                (Movie.title.ilike(f"%{query}%")) | (Movie.genre.ilike(f"%{query}%"))
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_average_rating(db: Session, movie_id: int) -> None:
        """Recalculate and update movie's average rating"""
        ratings = db.query(Rating).filter(Rating.movie_id == movie_id).all()
        if ratings:
            avg_rating = sum(r.score for r in ratings) / len(ratings)
            movie = db.query(Movie).filter(Movie.id == movie_id).first()
            if movie:
                movie.average_rating = avg_rating
                db.commit()
