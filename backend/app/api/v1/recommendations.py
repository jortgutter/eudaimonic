"""Recommendation endpoints"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db.database import get_db
from app.schemas import RecommendedMovieResponse, RecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/{user_id}", response_model=list[RecommendedMovieResponse], summary="List Recommendations")
def list_recommendations(
    user_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[RecommendedMovieResponse]:
    """Return the saved recommendations for a user."""
    items = RecommendationService.get_recommendation_items_for_user(db, user_id, limit)
    return [
        RecommendedMovieResponse(
            recommendation=RecommendationResponse.model_validate(recommendation),
            movie=movie,
        )
        for recommendation, movie in items
    ]


@router.post(
    "/{user_id}/generate",
    response_model=list[RecommendedMovieResponse],
    summary="Generate Recommendations",
)
def generate_recommendations(
    user_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[RecommendedMovieResponse]:
    """Recompute recommendations for a user and return the top results."""
    recommendations = RecommendationService.generate_recommendations(db, user_id, limit)
    return [
        RecommendedMovieResponse(
            recommendation=RecommendationResponse.model_validate(recommendation),
            movie=recommendation.movie,
        )
        for recommendation in recommendations
        if recommendation.movie is not None
    ]
