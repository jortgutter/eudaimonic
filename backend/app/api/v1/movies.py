"""Local movie catalog endpoints"""
from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.catalog import MovieCatalogItem, MovieVirtueScoresResponse
from backend.app.services.catalog_import_service import CatalogImportService
from backend.app.services.catalog_service import CatalogService


router = APIRouter(prefix="/movies", tags=["movies"])


@router.post(
    "/import/{tmdb_id}",
    response_model=MovieVirtueScoresResponse,
    summary="Import TMDb Movie Into Local Catalog",
)
def import_tmdb_movie(tmdb_id: int) -> MovieVirtueScoresResponse:
    """Import a TMDb movie into the database and score it."""
    CatalogImportService.import_movie(tmdb_id)
    scores = CatalogService.get_movie_virtue_scores(tmdb_id)
    if not scores:
        raise HTTPException(status_code=500, detail="Movie imported, but virtue scores could not be loaded")
    return scores

@router.get(
    "/by-ids",
    response_model=list[MovieCatalogItem],
    summary="Get Movies By IDs",
)
def get_movies_by_ids(
    ids: str = Query(..., description="Comma-separated list of movie IDs"),
) -> list[MovieCatalogItem]:
    """Fetch multiple movies by their IDs."""
    try:
        movie_ids = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid id list")

    return CatalogService.get_movies_by_ids(movie_ids)

@router.get("", response_model=list[MovieCatalogItem], summary="List Movies")
def list_movies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[MovieCatalogItem]:
    """Get paginated list of movies from the local catalog."""
    return CatalogService.list_movies(skip=skip, limit=limit)

@router.get(
    "/recommend",
    response_model=list[MovieCatalogItem],
    summary="Recommend Movies",
)
def recommend_movies(
    wisdom: float = Query(..., ge=0, le=1),
    courage: float = Query(..., ge=0, le=1),
    humanity: float = Query(..., ge=0, le=1),
    justice: float = Query(..., ge=0, le=1),
    temperance: float = Query(..., ge=0, le=1),
    transcendence: float = Query(..., ge=0, le=1),
    rating_weight: float = Query(..., ge=0, le=1),
    limit: int = Query(20, ge=1, le=100),
    exclude_ids: str | None = Query(None),
) -> list[MovieCatalogItem]:
    """Recommend movies based on virtue trait similarity."""

    return CatalogService.recommend_movies(
        wisdom=wisdom,
        courage=courage,
        humanity=humanity,
        justice=justice,
        temperance=temperance,
        transcendence=transcendence,
        rating_weight=rating_weight,
        limit=limit,
        exclude_ids=exclude_ids
    )


@router.get("/search", response_model=list[MovieCatalogItem], summary="Search Movies")
def search_movies(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[MovieCatalogItem]:
    """Search movies by title, summary, or genre."""
    return CatalogService.search_movies(query=q, skip=skip, limit=limit)


@router.get("/{movie_id}", response_model=MovieCatalogItem, summary="Get Movie")
def get_movie(movie_id: int) -> MovieCatalogItem:
    """Get a movie from the local catalog by ID."""
    movie = CatalogService.get_movie(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.get(
    "/{movie_id}/virtue-scores",
    response_model=MovieVirtueScoresResponse,
    summary="Get Movie Virtue Scores",
)
def get_movie_virtue_scores(movie_id: int) -> MovieVirtueScoresResponse:
    """Get virtue scores for a movie from the local catalog index."""
    scores = CatalogService.get_movie_virtue_scores(movie_id)
    if not scores:
        raise HTTPException(status_code=404, detail="Movie not found")
    return scores


@router.post("", summary="Create Movie")
def create_movie() -> None:
    """The local movie catalog is read-only."""
    raise HTTPException(status_code=405, detail="The local movie catalog is read-only")


@router.put("/{movie_id}", summary="Update Movie")
def update_movie(movie_id: int) -> None:
    """The local movie catalog is read-only."""
    raise HTTPException(status_code=405, detail="The local movie catalog is read-only")


@router.delete("/{movie_id}", summary="Delete Movie")
def delete_movie(movie_id: int) -> None:
    """The local movie catalog is read-only."""
    raise HTTPException(status_code=405, detail="The local movie catalog is read-only")
