"""Read-only access to the local movie catalog SQLite database."""
from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status, Query

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
    def _row_to_movie(
        row: sqlite3.Row,
        genres: list[str] | None = None
    ) -> MovieCatalogItem:

        release_date_value = row["release_date"] if "release_date" in row.keys() else None
        parsed_release_date: date | None = None

        if release_date_value:
            try:
                parsed_release_date = date.fromisoformat(str(release_date_value))
            except ValueError:
                parsed_release_date = None

        def v(key: str) -> float:
            return float(row[key]) if key in row.keys() and row[key] is not None else 0.0
        print(row.keys())
        return MovieCatalogItem(
            id=int(row["id"]),
            title=str(row["title"] or "Untitled"),
            summary=row["summary"],
            image_url=row["image_url"],
            vote_average=row["vote_average"],
            release_date=parsed_release_date,
            adult=bool(row["adult"] or 0),
            genres=genres or [],

            Wisdom=v("Wisdom"),
            Courage=v("Courage"),
            Humanity=v("Humanity"),
            Justice=v("Justice"),
            Temperance=v("Temperance"),
            Transcendence=v("Transcendence"),
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

                COUNT(DISTINCT r.id) AS review_count,

                COALESCE(GROUP_CONCAT(DISTINCT g.name), '') AS genres

            FROM movies m

            LEFT JOIN reviews r
                ON r.movie_id = m.id

            LEFT JOIN movie_genres mg
                ON mg.movie_id = m.id

            LEFT JOIN genres g
                ON g.id = mg.genre_id

            {where_clause}

            GROUP BY m.id

            ORDER BY review_count DESC,
                    m.vote_average DESC,
                    m.title ASC

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
            WHERE LOWER(m.title) LIKE LOWER(?)
        """


        params = (f"%{query}%",)

        return CatalogService._fetch_movie_rows(
            where_clause,
            params,
            skip=skip,
            limit=limit,
        )

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
        
    @staticmethod
    def recommend_movies(
        wisdom: float,
        courage: float,
        humanity: float,
        justice: float,
        temperance: float,
        transcendence: float,
        rating_weight: float,
        limit: int = 20,
        exclude_ids: str | None = None,
    ) -> list[MovieCatalogItem]:

        exclude_set: set[int] = set()

        if exclude_ids:
            exclude_set = {
                int(x)
                for x in exclude_ids.split(",")
                if x.strip().isdigit()
            }

        exclude_clause = ""
        params = {
            "wisdom": wisdom,
            "courage": courage,
            "humanity": humanity,
            "justice": justice,
            "temperance": temperance,
            "transcendence": transcendence,
            "rating_weight": rating_weight,
            "limit": limit,
        }

        # Only add exclusion SQL if needed
        if exclude_set:
            placeholders = ",".join(["?"] * len(exclude_set))
            exclude_clause = f"WHERE m.id NOT IN ({placeholders})"
            exclude_params = tuple(exclude_set)
        else:
            exclude_clause = ""
            exclude_params = tuple()

        query = f"""
            SELECT
                m.id,
                m.title,
                m.summary,
                m.image_url,
                m.vote_average,
                m.release_date,
                m.adult,

                vs.Wisdom,
                vs.Courage,
                vs.Humanity,
                vs.Justice,
                vs.Temperance,
                vs.Transcendence,

                COALESCE(GROUP_CONCAT(DISTINCT g.name), '') AS genres,

                (
                    (
                        CASE WHEN :wisdom = 0 THEN 0 ELSE (vs.Wisdom - :wisdom) * (vs.Wisdom - :wisdom) END +
                        CASE WHEN :courage = 0 THEN 0 ELSE (vs.Courage - :courage) * (vs.Courage - :courage) END +
                        CASE WHEN :humanity = 0 THEN 0 ELSE (vs.Humanity - :humanity) * (vs.Humanity - :humanity) END +
                        CASE WHEN :justice = 0 THEN 0 ELSE (vs.Justice - :justice) * (vs.Justice - :justice) END +
                        CASE WHEN :temperance = 0 THEN 0 ELSE (vs.Temperance - :temperance) * (vs.Temperance - :temperance) END +
                        CASE WHEN :transcendence = 0 THEN 0 ELSE (vs.Transcendence - :transcendence) * (vs.Transcendence - :transcendence) END
                    )
                    -
                    (:rating_weight * POWER(m.vote_average / 10.0, 2))
                ) AS score

            FROM movie_virtue_scores_wide vs
            JOIN movies m ON m.id = vs.movie_id
            LEFT JOIN reviews r ON r.movie_id = m.id
            LEFT JOIN movie_genres mg ON mg.movie_id = m.id
            LEFT JOIN genres g ON g.id = mg.genre_id

            {exclude_clause}

            GROUP BY m.id
            HAVING COUNT(r.id) >= 10

            ORDER BY score ASC
            LIMIT :limit
        """

        with CatalogService._connect() as connection:
            if exclude_set:
                rows = connection.execute(query, (*exclude_params, params["wisdom"], params["courage"], params["humanity"],
                                                params["justice"], params["temperance"], params["transcendence"],
                                                params["rating_weight"], params["limit"])).fetchall()
            else:
                rows = connection.execute(query, params).fetchall()

        items: list[MovieCatalogItem] = []

        for row in rows:
            genres = [g for g in str(row["genres"] or "").split(",") if g]
            items.append(CatalogService._row_to_movie(row, genres=genres))

        return items


    @staticmethod
    def get_movies_by_ids(movie_ids: list[int]) -> list[MovieCatalogItem]:
        if not movie_ids:
            return []

        placeholders = ",".join(["?"] * len(movie_ids))

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
            WHERE m.id IN ({placeholders})
            GROUP BY m.id
        """

        with CatalogService._connect() as connection:
            rows = connection.execute(query, movie_ids).fetchall()

        items: list[MovieCatalogItem] = []
        for row in rows:
            genres = [g for g in str(row["genres"] or "").split(",") if g]
            items.append(CatalogService._row_to_movie(row, genres=genres))

        return items