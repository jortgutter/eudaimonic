"""API v1 routes"""
from fastapi import APIRouter

from .movies import router as movies_router
from .health import router as health_router
from .chat import router as chat_router
from .tmdb import router as tmdb_router



router = APIRouter()
router.include_router(health_router)
router.include_router(movies_router)
router.include_router(chat_router)
router.include_router(tmdb_router)


__all__ = ["router"]