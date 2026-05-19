"""Read-only access to the local movie catalog SQLite database."""
from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from backend.app.schemas.catalog import MovieCatalogItem, MovieVirtueScoresResponse, VirtueScoreSet


class CatalogService:
    """Read-only service for the local catalog database."""

    @staticmethod
    def _candidate_paths() -> list[Path]:
        env_path = os.getenv("MOVIES_DB_PATH")
        candidates: list[Path] = []
        if env_path:
            candidates.append(Path(env_path).expanduser())

        backend_root = Path(__file__).resolve().parents[2]
        candidates.extend(
            [
                backend_root / "movies.db",
                backend_root / "data" / "movies.db",
                backend_root / "app" / "movies.db",
            ]
        )
        return candidates

    @staticmethod
    def _db_path() -> Path:
        for candidate in CatalogService._candidate_paths():
            if candidate.exists():
                return candidate

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Local movie catalog database not found. "
                "Set MOVIES_DB_PATH to the SQLite file path."
            ),
        )

    @staticmethod
    def _connect() -> sqlite3.Connection:
        path = CatalogService._db_path()
        try:
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        except sqlite3.Error as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not open local movie catalog: {exc}",
            ) from exc

        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _row_to_movie(row: sqlite3.Row, genres: list[str] | None = None) -> MovieCatalogItem:
        release_date_value = row["release_date"] if "release_date" in row.keys() else None
        parsed_release_date: date | None = None
        if release_date_value:
            try:
                parsed_release_date = date.fromisoformat(str(release_date_value))
            except ValueError:
                parsed_release_date = None

        return MovieCatalogItem(
            id=int(row["id"]),
            title=str(row["title"] or "Untitled"),
            summary=row["summary"],
            image_url=row["image_url"],
            vote_average=row["vote_average"],
            release_date=parsed_release_date,
            adult=bool(row["adult"] or 0),
            genres=genres or [],
        )

    @staticmethod
    def _genre_query_clause(search_term: str) -> tuple[str, tuple[Any, ...]]:
        return (
            """
            EXISTS (
                SELECT 1
                FROM movie_genres mg
                JOIN genres g ON g.id = mg.genre_id
                WHERE mg.movie_id = m.id
                  AND LOWER(g.name) LIKE LOWER(?)
            )
            """,
            (f"%{search_term}%",),
        )

    @staticmethod
    def _fetch_movie_rows(where_clause: str = "", params: tuple[Any, ...] = (), *, skip: int = 0, limit: int = 20) -> list[MovieCatalogItem]:
        query = f"""
            SELECT
                m.id,
                m.title,
                m.summary,
                m.image_url,
                m.vote_average,
                m.release_date,
                m.adult,
                COALESCE(GROUP_CONCAT(DISTINCT g.name), '') AS genres
            FROM movies m
            LEFT JOIN movie_genres mg ON mg.movie_id = m.id
            LEFT JOIN genres g ON g.id = mg.genre_id
            {where_clause}
            GROUP BY m.id
            ORDER BY m.release_date DESC, m.id DESC
            LIMIT ? OFFSET ?
        """
        with CatalogService._connect() as connection:
            rows = connection.execute(query, (*params, limit, skip)).fetchall()

        items: list[MovieCatalogItem] = []
        for row in rows:
            genres = [genre for genre in str(row["genres"] or "").split(",") if genre]
            items.append(CatalogService._row_to_movie(row, genres=genres))
        return items

    @staticmethod
    def list_movies(skip: int = 0, limit: int = 20) -> list[MovieCatalogItem]:
        return CatalogService._fetch_movie_rows(skip=skip, limit=limit)

    @staticmethod
    def get_movie(movie_id: int) -> MovieCatalogItem | None:
        with CatalogService._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    m.id,
                    m.title,
                    m.summary,
                    m.image_url,
                    m.vote_average,
                    m.release_date,
                    m.adult,
                    COALESCE(GROUP_CONCAT(DISTINCT g.name), '') AS genres
                FROM movies m
                LEFT JOIN movie_genres mg ON mg.movie_id = m.id
                LEFT JOIN genres g ON g.id = mg.genre_id
                WHERE m.id = ?
                GROUP BY m.id
                """,
                (movie_id,),
            ).fetchone()

        if row is None:
            return None

        genres = [genre for genre in str(row["genres"] or "").split(",") if genre]
        return CatalogService._row_to_movie(row, genres=genres)

    @staticmethod
    def search_movies(query: str, skip: int = 0, limit: int = 20) -> list[MovieCatalogItem]:
        where_clause = """
            WHERE (
                LOWER(m.title) LIKE LOWER(?)
                OR LOWER(COALESCE(m.summary, '')) LIKE LOWER(?)
                OR EXISTS (
                    SELECT 1
                    FROM movie_genres mg
                    JOIN genres g ON g.id = mg.genre_id
                    WHERE mg.movie_id = m.id
                      AND LOWER(g.name) LIKE LOWER(?)
                )
            )
        """
        params = (f"%{query}%", f"%{query}%", f"%{query}%")
        return CatalogService._fetch_movie_rows(where_clause, params, skip=skip, limit=limit)

    @staticmethod
    def get_movie_virtue_scores(movie_id: int) -> MovieVirtueScoresResponse | None:
        movie = CatalogService.get_movie(movie_id)
        if movie is None:
            return None

        with CatalogService._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    movie_id,
                    Wisdom,
                    Courage,
                    Humanity,
                    Justice,
                    Temperance,
                    Transcendence
                FROM movie_virtue_scores_wide
                WHERE movie_id = ?
                """,
                (movie_id,),
            ).fetchone()

        if row is None:
            virtue_scores = VirtueScoreSet()
        else:
            virtue_scores = VirtueScoreSet(
                wisdom=row["Wisdom"],
                courage=row["Courage"],
                humanity=row["Humanity"],
                justice=row["Justice"],
                temperance=row["Temperance"],
                transcendence=row["Transcendence"],
            )

        return MovieVirtueScoresResponse(movie=movie, virtue_scores=virtue_scores)