"""Local movie catalog endpoints"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
import traceback
from backend.app.schemas.catalog import MovieCatalogItem, MovieVirtueScoresResponse, WatchProviderItem
from backend.app.services.catalog_import_service import CatalogImportService
from backend.app.services.catalog_service import CatalogService
from pydantic import BaseModel

class BestMatchResponse(BaseModel):
    best_similar: MovieCatalogItem | None
    best_explore: MovieCatalogItem | None

router = APIRouter(prefix="/movies", tags=["movies"])


@router.post(
    "/import/{tmdb_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Import TMDb Movie Into Local Catalog",
)
def import_tmdb_movie(tmdb_id: int, background_tasks: BackgroundTasks) -> dict[str, object]:
    """Queue a TMDb movie import and return immediately."""
    background_tasks.add_task(CatalogImportService.import_movie_with_scores, tmdb_id)
    return {"status": "queued", "tmdb_id": tmdb_id}

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
    "/best-match",
    response_model=BestMatchResponse,
    summary="Best matching and best exploration movies for user profile",
)
def best_match_movies(
    wisdom: float = Query(..., ge=0, le=1),
    courage: float = Query(..., ge=0, le=1),
    humanity: float = Query(..., ge=0, le=1),
    justice: float = Query(..., ge=0, le=1),
    temperance: float = Query(..., ge=0, le=1),
    transcendence: float = Query(..., ge=0, le=1),
    wisdom_up: float = Query(...),
    courage_up: float = Query(...),
    humanity_up: float = Query(...),
    justice_up: float = Query(...),
    temperance_up: float = Query(...),
    transcendence_up: float = Query(...),

    exclude_ids: str | None = Query(None),
    provider_ids: str | None = Query(None),
    country_code: str = Query("NL", min_length=2, max_length=2),
):

    best_similar, best_explore =  CatalogService.best_match_movies(
        wisdom=wisdom,
        courage=courage,
        humanity=humanity,
        justice=justice,
        temperance=temperance,
        transcendence=transcendence,

        wisdom_up=wisdom_up,
        courage_up=courage_up,
        humanity_up=humanity_up,
        justice_up=justice_up,
        temperance_up=temperance_up,
        transcendence_up=transcendence_up,

        exclude_ids=exclude_ids,
        provider_ids=provider_ids,
        country_code=country_code,
    )
    
    return {
        "best_similar": best_similar,
        "best_explore": best_explore,
    }
    

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
    provider_ids: str | None = Query(None),
    country_code: str = Query("NL", min_length=2, max_length=2),
) -> list[MovieCatalogItem]:
    """Recommend movies based on virtue trait similarity."""
    try:


        return CatalogService.recommend_movies(
            wisdom=wisdom,
            courage=courage,
            humanity=humanity,
            justice=justice,
            temperance=temperance,
            transcendence=transcendence,
            rating_weight=rating_weight,
            limit=limit,
            exclude_ids=exclude_ids,
            provider_ids=provider_ids,
            country_code=country_code,
        )
    except Exception as e:
        print("\n\n=== RECOMMENDER ERROR ===")
        traceback.print_exc()
        print("=========================\n\n")
        raise


@router.get(
    "/watch-providers",
    response_model=list[WatchProviderItem],
    summary="List Watch Providers",
)
def list_watch_providers(
    country_code: str = Query("NL", min_length=2, max_length=2),
    provider_type: str | None = Query(None),
) -> list[WatchProviderItem]:
    """Return watch providers available in a country."""
    return CatalogService.list_watch_providers(
        country_code=country_code,
        provider_type=provider_type,
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
