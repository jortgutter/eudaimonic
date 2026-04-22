"""User endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db.database import get_db
from app.schemas import UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, summary="Create User")
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Create a user so the app has a user ID to rate with."""
    return UserService.create_user(db, user_in)


@router.get("", response_model=list[UserResponse], summary="List Users")
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List users to discover their IDs."""
    return UserService.list_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse, summary="Get User")
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get one user by ID."""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
