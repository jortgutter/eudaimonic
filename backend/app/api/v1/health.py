"""Health check endpoint"""
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Health Check")
def health_check():
    """Check API health status"""
    return {"status": "healthy", "message": "API is running"}
