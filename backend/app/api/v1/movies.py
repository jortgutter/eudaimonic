"""Local movie catalog endpoints"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
import traceback
from typing import Any
from backend.app.schemas.catalog import MovieCatalogItem, MovieVirtueScoresResponse, VirtueScoreSet, WatchProviderItem
from backend.app.services.catalog_import_service import CatalogImportService
from backend.app.services.catalog_service import CatalogService
from pydantic import BaseModel
import logging

class BestMatchResponse(BaseModel):
    best_similar: MovieCatalogItem | None
    best_explore: MovieCatalogItem | None

class ResponsiveRecommendResponse(BaseModel):
    best_match: MovieCatalogItem | None
    explore: MovieCatalogItem | None
    recommendations: list[MovieCatalogItem]

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
    except Exception:
        print("\n\n=== RECOMMENDER ERROR ===")
        traceback.print_exc()
        print("=========================\n\n")
        raise


# Full list of all 66 watch providers hardcoded directly from the database output
POPULAR_PROVIDERS = [
    WatchProviderItem(provider_id=196, provider_name="AcornTV Amazon Channel"),
    WatchProviderItem(provider_id=119, provider_name="Amazon Prime Video"),
    WatchProviderItem(provider_id=10, provider_name="Amazon Video"),
    WatchProviderItem(provider_id=350, provider_name="Apple TV"),
    WatchProviderItem(provider_id=2243, provider_name="Apple TV Amazon Channel"),
    WatchProviderItem(provider_id=2, provider_name="Apple TV Store"),
    WatchProviderItem(provider_id=381, provider_name="Canal+"),
    WatchProviderItem(provider_id=1968, provider_name="Crunchyroll Amazon Channel"),
    WatchProviderItem(provider_id=190, provider_name="Curiosity Stream"),
    WatchProviderItem(provider_id=603, provider_name="CuriosityStream Amazon Channel"),
    WatchProviderItem(provider_id=337, provider_name="Disney Plus"),
    WatchProviderItem(provider_id=396, provider_name="Film1"),
    WatchProviderItem(provider_id=701, provider_name="FilmBox+"),
    WatchProviderItem(provider_id=559, provider_name="Filmzie"),
    WatchProviderItem(provider_id=3, provider_name="Google Play Movies"),
    WatchProviderItem(provider_id=1899, provider_name="HBO Max"),
    WatchProviderItem(provider_id=1825, provider_name="HBO Max Amazon Channel"),
    WatchProviderItem(provider_id=563, provider_name="KPN"),
    WatchProviderItem(provider_id=2358, provider_name="Lionsgate+ Amazon Channels"),
    WatchProviderItem(provider_id=2141, provider_name="MGM Plus Amazon Channel"),
    WatchProviderItem(provider_id=11, provider_name="MUBI"),
    WatchProviderItem(provider_id=201, provider_name="MUBI Amazon Channel"),
    WatchProviderItem(provider_id=68, provider_name="Microsoft Store"),
    WatchProviderItem(provider_id=2565, provider_name="MovieMe"),
    WatchProviderItem(provider_id=472, provider_name="NLZIET"),
    WatchProviderItem(provider_id=1986, provider_name="NPO Plus"),
    WatchProviderItem(provider_id=360, provider_name="NPO Start"),
    WatchProviderItem(provider_id=8, provider_name="Netflix"),
    WatchProviderItem(provider_id=175, provider_name="Netflix Kids"),
    WatchProviderItem(provider_id=71, provider_name="Pathé Thuis"),
    WatchProviderItem(provider_id=688, provider_name="ShortsTV Amazon Channel"),
    WatchProviderItem(provider_id=1773, provider_name="SkyShowtime"),
    WatchProviderItem(provider_id=76, provider_name="Viaplay"),
    WatchProviderItem(provider_id=72, provider_name="Videoland"),
    WatchProviderItem(provider_id=297, provider_name="Ziggo TV"),
]

@router.get(
    "/watch-providers",
    response_model=list[WatchProviderItem],
    summary="List Watch Providers",
)
def list_watch_providers(
    country_code: str = Query("NL", min_length=2, max_length=2),
    provider_type: str | None = Query(None),
) -> list[WatchProviderItem]:
    """Return a curated list of popular watch providers instantly."""
    # Since it's a hardcoded list, we just return it directly.
    # (You can ignore country_code and provider_type here since these top brands are globally relevant)
    return POPULAR_PROVIDERS


@router.get("/search", response_model=list[MovieCatalogItem], summary="Search Movies")
def search_movies(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[MovieCatalogItem]:
    """Search movies by title, summary, or genre."""
    return CatalogService.search_movies(query=q, skip=skip, limit=limit)


@router.get(
    "/responsive-recommend",
    response_model=ResponsiveRecommendResponse,
    summary="Responsive Recommendations",
)
def responsive_recommend(
    watched_movie_ids: str = Query(..., description="Comma-separated list of watched movie IDs"),
    watched_ratings: str | None = Query(None, description="Comma-separated list of ratings aligned with watched_movie_ids"),
    selected_virtues: str | None = Query(None, description="Comma-separated list of selected virtues (e.g., Wisdom,Courage)"),
    provider_ids: str | None = Query(None, description="Comma-separated list of provider IDs"),
    country_code: str = Query("NL", min_length=2, max_length=2),
    limit: int = Query(20, ge=1, le=100),
):
    try:
        # Parse watched movie IDs
        watched_ids = [int(x) for x in watched_movie_ids.split(",") if x.strip().isdigit()]

        # Parse ratings (NEW)
        ratings = None
        if watched_ratings:
            parsed = [
                float(x) for x in watched_ratings.split(",")
                if x.strip()
            ]
            # align safety: only keep matching length
            ratings = parsed[: len(watched_ids)] if parsed else None

        # Parse selected virtues
        virtues_dict: dict[str, bool] = {}
        if selected_virtues:
            for virtue in selected_virtues.split(","):
                virtue = virtue.strip().capitalize()
                if virtue in ["Wisdom", "Courage", "Humanity", "Justice", "Temperance", "Transcendence"]:
                    virtues_dict[virtue] = True

        # Parse provider IDs
        provider_list: list[int] | None = None
        if provider_ids:
            provider_list = [int(x) for x in provider_ids.split(",") if x.strip().isdigit()]

        base_virtues = {
            "Wisdom": False,
            "Humanity": False,
            "Courage": False,
            "Justice": False,
            "Temperance": False,
            "Transcendence": False,
        }

        # 1. Best match
        best_match_list = CatalogService.responsive_recommend(
            watched_movie_ids=watched_ids,
            watched_ratings=ratings,   # NEW
            selected_virtues=base_virtues,
            provider_ids=provider_list,
            country_code=country_code,
            embedding_weight=0.7,
            virtue_weight=0.3,
            explore_factor=0.2,
            limit=1,
        )

        best_match = best_match_list[0] if best_match_list else None

        excluded_ids = []
        if best_match:
            excluded_ids.append(int(best_match.id))

        # 2. Explore
        explore_list = CatalogService.responsive_recommend(
            watched_movie_ids=watched_ids,
            watched_ratings=ratings,   # NEW
            disliked_ids=excluded_ids,
            selected_virtues=virtues_dict if virtues_dict else None,
            provider_ids=provider_list,
            country_code=country_code,
            explore_factor=1.0,
            limit=1,
        )

        explore = explore_list[0] if explore_list else None

        if explore:
            excluded_ids.append(int(explore.id))

        # 3. Recommendations
        recommendations = CatalogService.responsive_recommend(
            watched_movie_ids=watched_ids,
            watched_ratings=ratings,   # NEW
            disliked_ids=excluded_ids,
            selected_virtues=virtues_dict if virtues_dict else None,
            provider_ids=provider_list,
            country_code=country_code,
            explore_factor=0.3,
            limit=limit,
        )

        return {
            "best_match": best_match,
            "explore": explore,
            "recommendations": recommendations,
        }

    except Exception:
        print("\n\n=== RESPONSIVE RECOMMEND ERROR ===")
        traceback.print_exc()
        print("===================================\n\n")
        raise

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
    if scores:
        return scores
    
    # Movie not in local catalog yet - return placeholder with empty scores
    # The frontend will trigger the import in the background
    placeholder_movie = MovieCatalogItem(
        id=movie_id,
        title=f"Movie {movie_id}",
        summary=None,
        image_url=None,
        vote_average=None,
        release_date=None,
        adult=False,
        genres=[],
        Wisdom=0.0,
        Courage=0.0,
        Humanity=0.0,
        Justice=0.0,
        Temperance=0.0,
        Transcendence=0.0,
    )
    return MovieVirtueScoresResponse(
        movie=placeholder_movie,
        virtue_scores=VirtueScoreSet()
    )


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

