"""Read-only access to the local movie catalog DuckDB database."""
from __future__ import annotations
import math
import os
import re
import time
import duckdb
import numpy as np
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
import logging

from backend.app.schemas.catalog import MovieCatalogItem, MovieVirtueScoresResponse, VirtueScoreSet, WatchProviderItem

TRAITS = ["wisdom", "courage", "humanity", "justice", "temperance", "transcendence"]

def dot(a, b):
    return sum(a[t] * b[t] for t in TRAITS)


def norm(v):
    return math.sqrt(sum(v[t] * v[t] for t in TRAITS))


def normalize(v, eps=1e-8):
    n = norm(v)
    return {t: v[t] / (n + eps) for t in TRAITS}


def cosine_similarity(u, m):
    nu = normalize(u)
    nm = normalize(m)
    return dot(nu, nm)

class CatalogService:
    """Read-only service for the local catalog database."""

    @staticmethod
    def _candidate_paths() -> list[Path]:
        env_path = os.getenv("MOVIES_DB_PATH")
        backend_root = Path(__file__).resolve().parents[2]
        candidates: list[Path] = []
        if env_path:
            candidates.append(Path(env_path).expanduser())

        candidates.extend(
            [
                backend_root / "movies.db",
                backend_root / "data" / "movies.db",
                backend_root / "app" / "database" / "movies.db",
                backend_root / "app" / "movies.db",
            ]
        )
        return candidates

    @staticmethod
    def _db_path() -> Path:
        print("CWD:", Path.cwd())
        print("Candidates:")
        for candidate in CatalogService._candidate_paths():
            print(" -", candidate, "exists =", candidate.exists())
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
    def _connect() -> duckdb.DuckDBPyConnection:
        """Get a native DuckDB connection directly to the database file."""
        path = CatalogService._db_path()
        try:
            # Connect directly to the DuckDB file in read-only mode
            # This allows multiple FastAPI workers to read from it simultaneously without locks
            connection = duckdb.connect(database=str(path), read_only=True)
            connection.execute("SET default_null_order='NULLS LAST'")
            return connection
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not open local native movie catalog with DuckDB: {exc}",
            ) from exc

    @staticmethod
    def _row_to_movie(
        row: dict[str, Any],
        genres: list[str] | None = None
    ) -> MovieCatalogItem:
        """Converts a standardized column dictionary to a MovieCatalogItem."""
        release_date_value = row.get("release_date")
        parsed_release_date: date | None = None

        if release_date_value:
            try:
                parsed_release_date = date.fromisoformat(str(release_date_value))
            except ValueError:
                parsed_release_date = None

        def v(key: str) -> float:
            val = row.get(key)
            return float(val) if val is not None else 0.0

        return MovieCatalogItem(
            id=int(row.get("id") or 0),
            title=str(row.get("title") or "Untitled"),
            summary=row.get("summary"),
            image_url=row.get("image_url"),
            vote_average=row.get("vote_average"),
            release_date=parsed_release_date,
            adult=bool(row.get("adult") or 0),
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
            LEFT JOIN reviews r ON r.movie_id = m.id
            LEFT JOIN movie_genres mg ON mg.movie_id = m.id
            LEFT JOIN genres g ON g.id = mg.genre_id
            {where_clause}
            GROUP BY 
                m.id,
                m.title,
                m.summary,
                m.image_url,
                m.vote_average,
                m.release_date,
                m.adult
            ORDER BY review_count DESC,
                    m.vote_average DESC,
                    m.title ASC
            LIMIT ? OFFSET ?
        """
        with CatalogService._connect() as connection:
            result = connection.execute(query, (*params, limit, skip))
            col_names = result.columns if hasattr(result, 'columns') else []
            rows = result.fetchall()
        
        dict_rows = []
        if col_names:
            dict_rows = [dict(zip(col_names, row)) for row in rows]
        else:
            for row in rows:
                dict_rows.append({
                    'id': row[0], 'title': row[1], 'summary': row[2], 
                    'image_url': row[3], 'vote_average': row[4], 
                    'release_date': row[5], 'adult': row[6], 
                    'review_count': row[7], 'genres': row[8]
                })

        items: list[MovieCatalogItem] = []
        for row in dict_rows:
            genres = [genre for genre in str(row["genres"] or "").split(",") if genre]
            items.append(CatalogService._row_to_movie(row, genres=genres))
        return items

    @staticmethod
    def list_movies(skip: int = 0, limit: int = 20) -> list[MovieCatalogItem]:
        return CatalogService._fetch_movie_rows(skip=skip, limit=limit)

    @staticmethod
    def get_movie(movie_id: int) -> MovieCatalogItem | None:
        with CatalogService._connect() as connection:
            result = connection.execute(
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
                WHERE m.id = ? OR m.id = ?
                GROUP BY 
                    m.id,
                    m.title,
                    m.summary,
                    m.image_url,
                    m.vote_average,
                    m.release_date,
                    m.adult
                """,
                (int(movie_id), str(movie_id)),
            )
            
            row_tuple = result.fetchone()
            
            # 🚀 FIX: Reliable fallback columns list explicitly matched to your SELECT statement order
            if row_tuple:
                col_names = [col[0] for col in result.description] if result.description else [
                    'id', 'title', 'summary', 'image_url', 'vote_average', 'release_date', 'adult', 'genres'
                ]
                row = dict(zip(col_names, row_tuple))
            else:
                row = None

        if row is None:
            return None

        genres = [genre for genre in str(row.get("genres") or "").split(",") if genre]
        return CatalogService._row_to_movie(row, genres=genres)

    @staticmethod
    def search_movies(query: str, skip: int = 0, limit: int = 20) -> list[MovieCatalogItem]:
        where_clause = """
            WHERE LOWER(m.title) LIKE LOWER(?)
        """
        params = (f"%{query}%",)
        return CatalogService._fetch_movie_rows(where_clause, params, skip=skip, limit=limit)

    @staticmethod
    def get_movie_virtue_scores(movie_id: int) -> MovieVirtueScoresResponse | None:
        movie = CatalogService.get_movie(movie_id)
        if movie is None:
            logging.warning(f"get_movie_virtue_scores: Movie with id {movie_id} not found in catalog")
            return None

        with CatalogService._connect() as connection:
            result = connection.execute(
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
                WHERE movie_id = ? OR movie_id = ?
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (int(movie_id), str(movie_id)),
            )
            row_tuple = result.fetchone()
            col_names = result.columns if hasattr(result, 'columns') else [
                'movie_id', 'Wisdom', 'Courage', 'Humanity', 'Justice', 'Temperance', 'Transcendence'
            ]
            row = dict(zip(col_names, row_tuple)) if row_tuple else None

        if row is None:
            virtue_scores = VirtueScoreSet()
        else:
            virtue_scores = VirtueScoreSet(
                wisdom=float(row.get("Wisdom") or 0.0),
                courage=float(row.get("Courage") or 0.0),
                humanity=float(row.get("Humanity") or 0.0),
                justice=float(row.get("Justice") or 0.0),
                temperance=float(row.get("Temperance") or 0.0),
                transcendence=float(row.get("Transcendence") or 0.0),
            )
            # Sync true virtue traits down to the attached parent movie metadata
            movie.Wisdom = virtue_scores.wisdom
            movie.Courage = virtue_scores.courage
            movie.Humanity = virtue_scores.humanity
            movie.Justice = virtue_scores.justice
            movie.Temperance = virtue_scores.temperance
            movie.Transcendence = virtue_scores.transcendence

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
        provider_ids: str | None = None,
        country_code: str = "NL",
    ) -> list[MovieCatalogItem]:

        exclude_set: set[int] = set()
        if exclude_ids:
            exclude_set = {int(x) for x in exclude_ids.split(",") if x.strip().isdigit()}

        provider_set: set[int] = set()
        if provider_ids:
            provider_set = {int(x) for x in provider_ids.split(",") if x.strip().isdigit()}

        where_clauses: list[str] = ["m.vote_average >= 7"]
                
        params_map: dict[str, Any] = {
            "wisdom": wisdom,
            "courage": courage,
            "humanity": humanity,
            "justice": justice,
            "temperance": temperance,
            "transcendence": transcendence,
            "rating_weight": rating_weight,
            "limit": limit,
        }
        
        if exclude_set:
            placeholders = ",".join(f":exclude_{i}" for i in range(len(exclude_set)))
            for i, eid in enumerate(sorted(exclude_set)):
                params_map[f"exclude_{i}"] = eid
            where_clauses.append(f"m.id NOT IN ({placeholders})")

        if provider_set:
            provider_placeholders = ",".join([f":provider_{i}" for i, _ in enumerate(sorted(provider_set))])
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM watch_providers wp
                    WHERE wp.movie_id = m.id
                      AND UPPER(wp.country_code) = UPPER(:country_code)
                      AND wp.provider_id IN ({provider_placeholders})
                )
                """.replace("{provider_placeholders}", provider_placeholders)
            )

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        def build_query(min_reviews: int) -> str:
            return f"""
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
            {where_sql}
            GROUP BY 
                m.id, m.title, m.summary, m.image_url, m.vote_average, m.release_date, m.adult,
                vs.Wisdom, vs.Courage, vs.Humanity, vs.Justice, vs.Temperance, vs.Transcendence
            HAVING COUNT(r.id) >= {min_reviews}
            ORDER BY score ASC
            LIMIT :limit
        """

        if provider_set:
            for i, pid in enumerate(sorted(provider_set)):
                params_map[f"provider_{i}"] = pid
            params_map["country_code"] = country_code

        logger = logging.getLogger(__name__)

        with CatalogService._connect() as connection:
            min_reviews = 1 if provider_set else 10
            final_sql = build_query(min_reviews)
            result = connection.execute(final_sql, params_map)
            rows = result.fetchall()
            col_names = result.columns if hasattr(result, 'columns') else []
            
            dict_rows = [dict(zip(col_names, row)) for row in rows] if col_names else []

        items: list[MovieCatalogItem] = []
        for row in dict_rows:
            genres = [g for g in str(row.get("genres") or "").split(",") if g]
            items.append(CatalogService._row_to_movie(row, genres=genres))

        return items
    
    @staticmethod
    def sharpen_user_profile(user, k=8.0, temperature=0.7):
        values = np.array([user[t] for t in TRAITS])
        min_val = np.min(values)
        max_val = np.max(values)
        range_val = max_val - min_val if (max_val - min_val) != 0 else 1e-9
        return (values - min_val) / range_val
      
    @staticmethod
    def best_match_movies(
        wisdom: float,
        courage: float,
        humanity: float,
        justice: float,
        temperance: float,
        transcendence: float,
        wisdom_up: float,
        courage_up: float,
        humanity_up: float,
        justice_up: float,
        temperance_up: float,
        transcendence_up: float,
        exclude_ids: str | None = None,
        provider_ids: str | None = None,
        country_code: str = "NL",
    ) -> tuple[MovieCatalogItem, MovieCatalogItem]:

        logger = logging.getLogger(__name__)

        # -------------------------
        # Parse exclude IDs
        # -------------------------
        exclude_set: set[int] = set()
        if exclude_ids:
            exclude_set = {
                int(x)
                for x in exclude_ids.split(",")
                if x.strip().isdigit()
            }

        # -------------------------
        # Parse provider IDs
        # -------------------------
        provider_set: set[int] = set()
        if provider_ids:
            provider_set = {
                int(x)
                for x in provider_ids.split(",")
                if x.strip().isdigit()
            }

        # -------------------------
        # WHERE clause builder
        # -------------------------
        where_clauses: list[str] = []
        
        # Filter out movies below 7 rating
        where_clauses.append("m.vote_average >= 7")

        if exclude_set:
            placeholders = ",".join([f":exclude_{i}" for i in range(len(exclude_set))])
            where_clauses.append(f"m.id NOT IN ({placeholders})")

        if provider_set:
            provider_placeholders = ",".join([f":provider_{i}" for i in range(len(provider_set))])
            where_clauses.append(f"""
                EXISTS (
                    SELECT 1
                    FROM watch_providers wp
                    WHERE wp.movie_id = m.id
                    AND UPPER(wp.country_code) = UPPER(:country_code)
                    AND wp.provider_id IN ({provider_placeholders})
                )
            """)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        trait_scores = {
            "wisdom": wisdom_up,
            "courage": courage_up,
            "humanity": humanity_up,
            "justice": justice_up,
            "temperance": temperance_up,
            "transcendence": transcendence_up,
        }
        print(f'trait scores:\n{trait_scores}')
        
        stabilized_trait_scores = CatalogService.sharpen_user_profile(user=trait_scores)
        print(f'stabilized trait scores:\n{stabilized_trait_scores}')
        sorted_traits = sorted(trait_scores.items(), key=lambda x: x[1], reverse=True)
        sorted_traits = sorted(trait_scores.items(), key=lambda x: x[1], reverse=True)

        top_traits = sorted_traits[:3]
        bottom_traits = sorted_traits[-3:]

        # -------------------------
        # Shared SQL with mode-based scoring
        # -------------------------
        sql = f"""
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
                    :w1 * (
                        CASE :t1
                            WHEN 'wisdom' THEN vs.Wisdom
                            WHEN 'courage' THEN vs.Courage
                            WHEN 'humanity' THEN vs.Humanity
                            WHEN 'justice' THEN vs.Justice
                            WHEN 'temperance' THEN vs.Temperance
                            WHEN 'transcendence' THEN vs.Transcendence
                        END
                    )
                    +
                    :w2 * (
                        CASE :t2
                            WHEN 'wisdom' THEN vs.Wisdom
                            WHEN 'courage' THEN vs.Courage
                            WHEN 'humanity' THEN vs.Humanity
                            WHEN 'justice' THEN vs.Justice
                            WHEN 'temperance' THEN vs.Temperance
                            WHEN 'transcendence' THEN vs.Transcendence
                        END
                    )
                    +
                    :w3 * (
                        CASE :t3
                            WHEN 'wisdom' THEN vs.Wisdom
                            WHEN 'courage' THEN vs.Courage
                            WHEN 'humanity' THEN vs.Humanity
                            WHEN 'justice' THEN vs.Justice
                            WHEN 'temperance' THEN vs.Temperance
                            WHEN 'transcendence' THEN vs.Transcendence
                        END
                    )
                )
                +
                :pop_weight * (m.vote_average / 10.0) AS score

            FROM movie_virtue_scores_wide vs
            JOIN movies m ON m.id = vs.movie_id

            LEFT JOIN reviews r ON r.movie_id = m.id
            LEFT JOIN movie_genres mg ON mg.movie_id = m.id
            LEFT JOIN genres g ON g.id = mg.genre_id

            {where_sql}

            GROUP BY m.id

            HAVING COUNT(r.id) >= :min_reviews

            ORDER BY score DESC

            LIMIT 1;
"""
      

        # -------------------------
        # Base parameters
        # -------------------------
        
        base_params: dict[str, Any] = {
            "pop_weight": 0.00,
            "w1":0.6,
            "w2": 2.3,
            "w3": 0.1,
            "t1": sorted_traits[0][0],
            "t2": sorted_traits[1][0],
            "t3": sorted_traits[2][0],
        }

        min_reviews = 1 if provider_set else 10
        base_params["min_reviews"] = min_reviews

        if provider_set:
            for i, pid in enumerate(sorted(provider_set)):
                base_params[f"provider_{i}"] = pid
            base_params["country_code"] = country_code

        if exclude_set:
            for i, eid in enumerate(sorted(exclude_set)):
                base_params[f"exclude_{i}"] = eid
                
        def build_params(mode: str):
            if mode == "similar":
                traits = top_traits
                weights = [0.6, 0.3, 0.1]
            else:
                traits = bottom_traits
                weights = [0.6, 0.3, 0.1]

            return {
                "pop_weight": 0.4,

                "w1": weights[0],
                "w2": weights[1],
                "w3": weights[2],

                "t1": traits[0][0],
                "t2": traits[1][0],
                "t3": traits[2][0],

                "min_reviews": 1 if provider_set else 10,
                **({
                    f"provider_{i}": pid
                    for i, pid in enumerate(sorted(provider_set))
                } if provider_set else {}),
                **({
                    f"exclude_{i}": eid
                    for i, eid in enumerate(sorted(exclude_set))
                } if exclude_set else {}),
                **({"country_code": country_code} if provider_set else {}),
            }
        # -------------------------
        # Helper execution function
        # -------------------------
        def execute(mode: str) -> MovieCatalogItem:
            params = build_params(mode)

            with CatalogService._connect() as connection:
                result = connection.execute(sql, params)
                row_tuple = result.fetchone()
                col_names = result.columns if hasattr(result, 'columns') else []
                row = dict(zip(col_names, row_tuple)) if (row_tuple and col_names) else None

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No matching movie found for mode={mode}",
                )

            genres = [g for g in str(row.get("genres") or "").split(",") if g]
            return CatalogService._row_to_movie(row, genres=genres)

        # -------------------------
        # Execute both modes
        # -------------------------
        best_similar = execute("similar")
        best_explore = execute("explore")

        return best_similar, best_explore

    @staticmethod
    def list_watch_providers(
        country_code: str = "NL",
        provider_type: str | None = None,
    ) -> list[WatchProviderItem]:
        # Explicit collection of popular provider IDs (e.g., Netflix, Prime, Disney+, Apple, HBO, Videoland, SkyShowtime, Pathé Thuis, NPO, NLZIET)
        POPULAR_PROVIDER_IDS = (
            8,     # Netflix
            119,   # Amazon Prime Video
            337,   # Disney Plus
            2,     # Apple TV / iTunes
            350,   # Apple TV Plus
            1899,  # HBO Max
            72,    # Videoland
            1773,  # SkyShowtime
            472,   # NLZIET
            1986,  # NPO Plus
            3,     # Google Play Movies
            68,    # Microsoft Store
            35,    # Rakuten TV
            76,    # Viaplay
            1824,  # Pathé Thuis
        )

        query = f"""
            SELECT DISTINCT
                provider_id,
                provider_name
            FROM watch_providers
            WHERE UPPER(country_code) = UPPER(?)
              AND provider_id IN {POPULAR_PROVIDER_IDS}
        """
        params: list[Any] = [country_code]

        if provider_type:
            query += " AND LOWER(provider_type) = LOWER(?)"
            params.append(provider_type)

        query += " ORDER BY provider_name ASC"

        with CatalogService._connect() as connection:
            result = connection.execute(query, tuple(params))
            rows = result.fetchall()
            col_names = result.columns if hasattr(result, 'columns') else []
            dict_rows = [dict(zip(col_names, r)) for r in rows] if col_names else []

        providers: list[WatchProviderItem] = []
        for row in dict_rows:
            providers.append(
                WatchProviderItem(
                    provider_id=int(row.get("provider_id") or 0),
                    provider_name=str(row.get("provider_name") or "Unknown"),
                )
            )

        return providers


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
            result = connection.execute(query, movie_ids)
            rows = result.fetchall()
            col_names = result.columns if hasattr(result, 'columns') else []
            dict_rows = [dict(zip(col_names, r)) for r in rows] if col_names else []

        items: list[MovieCatalogItem] = []
        for row in dict_rows:
            genres = [g for g in str(row.get("genres") or "").split(",") if g]
            items.append(CatalogService._row_to_movie(row, genres=genres))

        return items
    
    @staticmethod
    def responsive_recommend(
        watched_movie_ids: list[int],
        watched_ratings: list[float] | None = None,
        liked_ids: list[int] | None = None,
        disliked_ids: list[int] | None = None,
        selected_virtues: dict[str, bool] | None = None,
        limit: int = 10,
        virtue_weight: float = 0.95,
        embedding_weight: float = 0.05,
        boost_factor: float = 1.5,
        provider_ids: list[int] | None = None, 
        country_code: str = "NL",
        explore_factor: float = 0.0,
    ) -> list[MovieCatalogItem]:
        if not watched_movie_ids:
            return []

        watched_ids = [int(x) for x in watched_movie_ids]

        # PROVIDER FILTER
        provider_filter_sql = ""
        provider_params: list[Any] = []

        if provider_ids is None:
            provider_ids = [8]

        if provider_ids:
            provider_placeholders = ",".join(["?"] * len(provider_ids))
            provider_filter_sql = f"""
            AND EXISTS (
                SELECT 1
                FROM watch_providers wp
                WHERE wp.movie_id = m.id
                  AND wp.country_code = ?
                  AND wp.provider_id IN ({provider_placeholders})
            )
            """
            provider_params = [country_code] + provider_ids

        if liked_ids is None:
            liked_ids = []

        if disliked_ids is None:
            disliked_ids = []

        if watched_ratings is not None:
            watched_ratings = (
                watched_ratings + [5] * len(watched_ids)
            )[:len(watched_ids)]

            for mid, rating in zip(watched_ids, watched_ratings):
                if rating >= 7 and mid not in liked_ids:
                    liked_ids.append(mid)
                elif rating <= 4 and mid not in disliked_ids:
                    disliked_ids.append(mid)

        # Use the class connection helper to handle connection & attachment safely
        with CatalogService._connect() as conn:

            if liked_ids:
                rows = conn.execute(f"""
                    SELECT movie_id, embedding
                    FROM movie_embeddings
                    WHERE movie_id IN ({",".join(["?"] * len(liked_ids))})
                """, liked_ids).fetchall()

                emb_map = {mid: np.array(e) for mid, e in rows}
                liked_embs = np.array([emb_map[mid] for mid in liked_ids])

                weights = np.linspace(1.0, 3.0, len(liked_ids))
                weights /= weights.sum()

                liked_profile = np.average(liked_embs, axis=0, weights=weights)
            else:
                liked_profile = None

            liked_ids = [int(x) for x in liked_ids] if liked_ids else []
            disliked_ids = [int(x) for x in disliked_ids] if disliked_ids else []

            # LIKED EMBEDDING PROFILE
            if liked_ids:
                liked_embs = np.array([
                    list(e[0]) for e in conn.execute(f"""
                        SELECT embedding
                        FROM movie_embeddings
                        WHERE movie_id IN ({",".join(["?"] * len(liked_ids))})
                    """, liked_ids).fetchall()
                ])

                weights = np.linspace(1.0, 3.0, len(liked_ids))
                weights /= weights.sum()

                liked_profile = np.average(liked_embs, axis=0, weights=weights)
            else:
                liked_profile = None

            # VIRTUE PROFILE (BASE)
            if liked_ids:
                liked_virtues = np.array(conn.execute(f"""
                    SELECT AVG(Wisdom),
                           AVG(Courage),
                           AVG(Humanity),
                           AVG(Justice),
                           AVG(Temperance),
                           AVG(Transcendence)
                    FROM movie_virtue_scores_wide
                    WHERE movie_id IN ({",".join(["?"] * len(liked_ids))})
                """, liked_ids).fetchone())
            else:
                liked_virtues = np.zeros(6)

            # LOAD WATCHED CLUSTERS
            watched_clusters = conn.execute(f"""
                SELECT cluster_id
                FROM movie_clusters
                WHERE movie_id IN ({",".join(["?"] * len(watched_ids))})
            """, watched_ids).fetchall()

            watched_clusters = [c[0] for c in watched_clusters]
            bad_clusters = set(watched_clusters)

            # WATCHED TITLES (FRANCHISE BLOCK)
            watched_titles = conn.execute(f"""
                SELECT title
                FROM movies
                WHERE id IN ({",".join(["?"] * len(watched_ids))})
            """, watched_ids).fetchall()

            watched_titles = [t[0].lower() for t in watched_titles]

            def extract_words(text):
                return set(re.findall(r"\w+", text.lower()))

            watched_keywords = set()
            for t in watched_titles:
                watched_keywords |= extract_words(t)

            def shares_franchise(title):
                words = extract_words(title)
                return len(words & watched_keywords) >= 2
            
            exclude_ids = list(set(watched_ids + (disliked_ids if disliked_ids else [])))
            exclude_placeholders = ",".join(["?"] * len(exclude_ids))
            
            # Define your minimum review count requirement
            min_reviews = 2  # Or pass this as a parameter to the method if preferred
            
            exclude_ids = list(set(watched_ids + (disliked_ids if disliked_ids else [])))
            exclude_placeholders = ",".join(["?"] * len(exclude_ids))

            # CANDIDATES (Filtered by minimum review count)
            candidates = conn.execute(f"""
                SELECT m.id,
                       m.title,
                       e.embedding,
                       v.Wisdom, v.Courage, v.Humanity,
                       v.Justice, v.Temperance, v.Transcendence,
                       mc.cluster_id
                FROM movies m
                JOIN movie_embeddings e ON m.id = e.movie_id
                JOIN movie_virtue_scores_wide v ON m.id = v.movie_id
                JOIN movie_clusters mc ON m.id = mc.movie_id
                LEFT JOIN reviews r ON r.movie_id = m.id    
                WHERE m.id NOT IN ({exclude_placeholders})
                  AND m.vote_average >= 7
                  {provider_filter_sql}
                GROUP BY                                    
                       m.id,
                       m.title,
                       e.embedding,
                       v.Wisdom, v.Courage, v.Humanity,
                       v.Justice, v.Temperance, v.Transcendence,
                       mc.cluster_id
                HAVING COUNT(r.id) >= ?                        
            """, exclude_ids + provider_params + [min_reviews]).fetchall()

            if not candidates:
                return []

            candidate_ids = np.array([c[0] for c in candidates])
            candidate_titles = np.array([c[1] for c in candidates])
            candidate_embs = np.array([list(c[2]) for c in candidates])
            candidate_virtues = np.array([c[3:9] for c in candidates], dtype=float)
            candidate_clusters = np.array([c[9] for c in candidates])

            # HARD FRANCHISE FILTER
            mask = np.array([
                not shares_franchise(t)
                for t in candidate_titles
            ])

            candidate_ids = candidate_ids[mask]
            candidate_titles = candidate_titles[mask]
            candidate_embs = candidate_embs[mask]
            candidate_virtues = candidate_virtues[mask]
            candidate_clusters = candidate_clusters[mask]

            if len(candidate_ids) == 0:
                return []

            # EMBEDDING SCORE
            emb_sims = np.zeros(len(candidate_ids))

            if liked_profile is not None:
                emb_sims += candidate_embs @ liked_profile

            if len(emb_sims) > 1:
                emb_sims = (emb_sims - emb_sims.min()) / (np.ptp(emb_sims) + 1e-9)

            # VIRTUE SCORE
            virtue_names = [
                "Wisdom", "Courage", "Humanity",
                "Justice", "Temperance", "Transcendence"
            ]

            target_virtues = liked_virtues.astype(float).copy()

            if selected_virtues:
                for i, name in enumerate(virtue_names):
                    if selected_virtues.get(name, False):
                        target_virtues[i] *= boost_factor
                    else:
                        target_virtues[i] *= 0.85

            tnorm = np.linalg.norm(target_virtues)

            weights = np.ones(6)
            if selected_virtues:
                for i, name in enumerate(virtue_names):
                    if selected_virtues.get(name, False):
                        weights[i] = boost_factor
                    else:
                        weights[i] = 0.8

            virtue_sims = np.array([
                np.dot(weights * liked_virtues, v * weights) /
                (np.linalg.norm(weights * liked_virtues) * np.linalg.norm(v * weights) + 1e-9)
                for v in candidate_virtues
            ])

            # stabilize + amplify signal
            virtue_sims = np.tanh(2.0 * virtue_sims)

            # NOVELTY
            lnorm = np.linalg.norm(liked_virtues)

            novelty = np.array([
                1 - (
                    np.dot(liked_virtues, v) /
                    (lnorm * np.linalg.norm(v))
                )
                if lnorm > 0 and np.linalg.norm(v) > 0 else 0
                for v in candidate_virtues
            ])

            if len(novelty) > 1:
                novelty = (novelty - novelty.min()) / (np.ptp(novelty) + 1e-9)

            # CLUSTER HOPPING
            cluster_penalty = np.array([
                1.0 if c not in bad_clusters else 0.2
                for c in candidate_clusters
            ])

            if explore_factor > 0.4:
                cluster_penalty = np.array([
                    1.0 if c not in bad_clusters else 0.0
                    for c in candidate_clusters
                ])

            # SCORES
            base_score = (
                embedding_weight * emb_sims +
                virtue_weight * virtue_sims
            )

            explore_score = (
                0.10 * emb_sims +
                0.25 * novelty +
                0.30 * cluster_penalty +
                0.35 * virtue_sims
            )

            combined = (
                (1 - explore_factor) * base_score +
                explore_factor * explore_score
            )

            # TOP RESULTS
            top_idx = np.argsort(-combined)[:limit]
            top_ids = candidate_ids[top_idx]

            result_rel = conn.query(f"""
                        SELECT 
                            m.id,
                            m.title,
                            m.summary,
                            m.image_url,
                            m.vote_average,
                            m.release_date,
                            m.adult,
                            COALESCE(GROUP_CONCAT(DISTINCT g.name), '') AS genres,
                            v.Wisdom,
                            v.Courage,
                            v.Humanity,
                            v.Justice,
                            v.Temperance,
                            v.Transcendence
                        FROM movies m
                        JOIN movie_virtue_scores_wide v ON m.id = v.movie_id
                        LEFT JOIN movie_genres mg ON mg.movie_id = m.id
                        LEFT JOIN genres g ON g.id = mg.genre_id
                        WHERE m.id IN ({",".join(["?"] * len(top_ids))})
                        GROUP BY 
                            m.id, 
                            m.title, 
                            m.summary, 
                            m.image_url, 
                            m.vote_average, 
                            m.release_date, 
                            m.adult,
                            v.Wisdom,
                            v.Courage,
                            v.Humanity,
                            v.Justice,
                            v.Temperance,
                            v.Transcendence
                    """, params=list(map(int, top_ids)))
            
            col_names = result_rel.columns
            result_rows = result_rel.fetchall()
            
            items: list[MovieCatalogItem] = []
            for row_tuple in result_rows:
                row = dict(zip(col_names, row_tuple))
                genres = [g for g in str(row.get("genres") or "").split(",") if g]
                item = CatalogService._row_to_movie(row, genres=genres)
                item.Wisdom = float(row.get("Wisdom") or 0.0)
                item.Courage = float(row.get("Courage") or 0.0)
                item.Humanity = float(row.get("Humanity") or 0.0)
                item.Justice = float(row.get("Justice") or 0.0)
                item.Temperance = float(row.get("Temperance") or 0.0)
                item.Transcendence = float(row.get("Transcendence") or 0.0)
                items.append(item)

        # Note: conn.close() happens automatically on leaving the context block!
        return items