"""TMDb endpoints"""
from fastapi import APIRouter, Depends
from sqlmodel import Session

<<<<<<< HEAD
from app.db.database import get_db
from app.schemas import TmdbImportResponse, TmdbSearchResponse
from app.services.tmdb_service import TmdbService

=======
from backend.app.db.database import get_db
from backend.app.schemas import TmdbImportResponse, TmdbSearchResponse, TmdbMovieSummary
from backend.app.services.tmdb_service import TmdbService
from backend.app.schemas.catalog import MovieCatalogItem, MovieVirtueScoresResponse, WatchProviderItem
from backend.app.services.catalog_import_service import CatalogImportService
from backend.app.services.catalog_service import CatalogService
import traceback
>>>>>>> origin/Movie-virtue-auto-importer
router = APIRouter(prefix="/tmdb", tags=["tmdb"])


# @router.get("/search", response_model=TmdbSearchResponse, summary="Search TMDb")
# async def search_tmdb(q: str, page: int = 1) -> TmdbSearchResponse:
#     """Search TMDb for movies"""

#     return await TmdbService.search_movies(query=q, page=page)

@router.get("/search", response_model=TmdbSearchResponse)
async def search_tmdb(q: str, page: int = 1) -> TmdbSearchResponse:
    return await TmdbService.search_movies(query=q, page=page)


@router.post(
    "/import/{tmdb_id}",
    response_model=TmdbImportResponse,
    summary="Import TMDb movie",
)
async def import_tmdb_movie(tmdb_id: int, db: Session = Depends(get_db)) -> TmdbImportResponse:
    """Import a TMDb movie into the local database"""
    movie = await TmdbService.import_movie(db, tmdb_id)
    return movie
