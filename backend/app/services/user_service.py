"""User business logic"""
from sqlmodel import Session

from app.db.models import User
from app.schemas import UserCreate


class UserService:
    """Service for user operations"""

    @staticmethod
    def create_user(db: Session, user_in: UserCreate) -> User:
        """Create a new user."""
        user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=user_in.password,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def list_users(db: Session, skip: int = 0, limit: int = 50) -> list[User]:
        """List users so clients can discover user IDs."""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def get_user(db: Session, user_id: int) -> User | None:
        """Get a single user by ID."""
        return db.query(User).filter(User.id == user_id).first()
