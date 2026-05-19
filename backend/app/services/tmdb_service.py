"""TMDb integration service"""
from __future__ import annotations

import httpx
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import get_settings
from app.db.models import Movie
from app.schemas import MovieCreate, TmdbMovieSummary, TmdbSearchResponse


class TmdbService:
    """Fetches movie catalog data from TMDb and imports it into the local DB."""

    _genre_cache: dict[str, int] | None = None

    @staticmethod
    def _settings():
        return get_settings()

    @staticmethod
    def _base_url() -> str:
        return TmdbService._settings().TMDB_BASE_URL.rstrip("/")

    @staticmethod
    def _image_url(path: str | None) -> str | None:
        if not path:
            return None
        settings = TmdbService._settings()
        return f"{settings.TMDB_IMAGE_BASE_URL.rstrip('/')}{path}"

    @staticmethod
    async def search_movies(query: str, page: int = 1) -> TmdbSearchResponse:
        settings = TmdbService._settings()
        if not settings.TMDB_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TMDb API key is not configured on the backend.",
            )

        params = {
            "api_key": settings.TMDB_API_KEY,
            "query": query,
            "page": page,
            "include_adult": "false",
            "language": "en-US",
        }

        async with httpx.AsyncClient(timeout=settings.TMDB_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{TmdbService._base_url()}/search/movie", params=params)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"TMDb search failed: {response.text}",
            )

        data = response.json()
        results = [
            TmdbMovieSummary(
                id=item["id"],
                title=item.get("title") or item.get("name") or "Untitled",
                overview=item.get("overview"),
                poster_url=TmdbService._image_url(item.get("poster_path")),
                release_date=item.get("release_date"),
                vote_average=float(item.get("vote_average") or 0.0),
                popularity=float(item.get("popularity") or 0.0),
                genre_ids=list(item.get("genre_ids") or []),
            )
            for item in data.get("results", [])
        ]

        return TmdbSearchResponse(
            page=data.get("page", page),
            total_results=data.get("total_results", 0),
            total_pages=data.get("total_pages", 0),
            results=results,
        )

    @staticmethod
    def get_genre_map() -> dict[str, int]:
        """Return a case-insensitive genre name to TMDb genre id map."""
        if TmdbService._genre_cache is not None:
            return TmdbService._genre_cache

        settings = TmdbService._settings()
        if not settings.TMDB_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TMDb API key is not configured on the backend.",
            )

        params = {"api_key": settings.TMDB_API_KEY, "language": "en-US"}
        with httpx.Client(timeout=settings.TMDB_TIMEOUT_SECONDS) as client:
            response = client.get(f"{TmdbService._base_url()}/genre/movie/list", params=params)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"TMDb genre lookup failed: {response.text}",
            )

        data = response.json()
        genre_map = {
            str(item.get("name", "")).strip().lower(): int(item["id"])
            for item in data.get("genres", [])
            if item.get("name") and item.get("id") is not None
        }
        TmdbService._genre_cache = genre_map
        return genre_map

    @staticmethod
    def discover_movies(
        genre_ids: list[int] | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> TmdbSearchResponse:
        """Discover candidate movies from TMDb using genre filters and popularity."""
        settings = TmdbService._settings()
        if not settings.TMDB_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TMDb API key is not configured on the backend.",
            )

        params: dict[str, object] = {
            "api_key": settings.TMDB_API_KEY,
            "language": "en-US",
            "include_adult": "false",
            "sort_by": "popularity.desc",
            "page": page,
            "vote_count.gte": 25,
        }
        if genre_ids:
            params["with_genres"] = ",".join(str(genre_id) for genre_id in genre_ids)

        with httpx.Client(timeout=settings.TMDB_TIMEOUT_SECONDS) as client:
            response = client.get(f"{TmdbService._base_url()}/discover/movie", params=params)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"TMDb discover failed: {response.text}",
            )

        data = response.json()
        results = [
            TmdbMovieSummary(
                id=item["id"],
                title=item.get("title") or item.get("name") or "Untitled",
                overview=item.get("overview"),
                poster_url=TmdbService._image_url(item.get("poster_path")),
                release_date=item.get("release_date"),
                vote_average=float(item.get("vote_average") or 0.0),
                popularity=float(item.get("popularity") or 0.0),
                genre_ids=list(item.get("genre_ids") or []),
            )
            for item in data.get("results", [])[:limit]
        ]

        return TmdbSearchResponse(
            page=data.get("page", page),
            total_results=data.get("total_results", 0),
            total_pages=data.get("total_pages", 0),
            results=results,
        )

    @staticmethod
    async def import_movie(db: Session, tmdb_id: int) -> Movie:
        settings = TmdbService._settings()
        if not settings.TMDB_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TMDb API key is not configured on the backend.",
            )

        existing = db.query(Movie).filter(Movie.tmdb_id == tmdb_id).first()
        if existing:
            return existing

        params = {"api_key": settings.TMDB_API_KEY, "language": "en-US"}
        async with httpx.AsyncClient(timeout=settings.TMDB_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{TmdbService._base_url()}/movie/{tmdb_id}", params=params)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"TMDb movie fetch failed: {response.text}",
            )

        data = response.json()
        release_date = data.get("release_date") or ""
        release_year = int(release_date[:4]) if len(release_date) >= 4 and release_date[:4].isdigit() else None
        genres = ",".join([genre.get("name", "") for genre in data.get("genres", []) if genre.get("name")]) or None

        movie_in = MovieCreate(
            tmdb_id=tmdb_id,
            title=data.get("title") or data.get("original_title") or "Untitled",
            description=data.get("overview"),
            release_year=release_year,
            genre=genres,
            poster_url=TmdbService._image_url(data.get("poster_path")),
            imdb_id=data.get("imdb_id"),
        )

        movie = Movie(**movie_in.model_dump())
        movie.average_rating = float(data.get("vote_average") or 0.0)
        db.add(movie)
        db.commit()
        db.refresh(movie)
        return movie

    @staticmethod
    def import_movie_sync(db: Session, tmdb_id: int) -> Movie:
        """Synchronous variant used by recommendation generation."""
        settings = TmdbService._settings()
        if not settings.TMDB_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TMDb API key is not configured on the backend.",
            )

        existing = db.query(Movie).filter(Movie.tmdb_id == tmdb_id).first()
        if existing:
            return existing

        params = {"api_key": settings.TMDB_API_KEY, "language": "en-US"}
        with httpx.Client(timeout=settings.TMDB_TIMEOUT_SECONDS) as client:
            response = client.get(f"{TmdbService._base_url()}/movie/{tmdb_id}", params=params)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"TMDb movie fetch failed: {response.text}",
            )

        data = response.json()
        release_date = data.get("release_date") or ""
        release_year = int(release_date[:4]) if len(release_date) >= 4 and release_date[:4].isdigit() else None
        genres = ",".join([genre.get("name", "") for genre in data.get("genres", []) if genre.get("name")]) or None

        movie_in = MovieCreate(
            tmdb_id=tmdb_id,
            title=data.get("title") or data.get("original_title") or "Untitled",
            description=data.get("overview"),
            release_year=release_year,
            genre=genres,
            poster_url=TmdbService._image_url(data.get("poster_path")),
            imdb_id=data.get("imdb_id"),
        )

        movie = Movie(**movie_in.model_dump())
        movie.average_rating = float(data.get("vote_average") or 0.0)
        db.add(movie)
        db.commit()
        db.refresh(movie)
        return movie
