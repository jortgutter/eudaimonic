"""Read-only access to the local movie catalog SQLite database."""
from __future__ import annotations
import math
import os
import sqlite3
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
                ORDER BY rowid DESC
                LIMIT 1
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
        provider_ids: str | None = None,
        country_code: str = "NL",
    ) -> list[MovieCatalogItem]:

        exclude_set: set[int] = set()

        if exclude_ids:
            exclude_set = {
                int(x)
                for x in exclude_ids.split(",")
                if x.strip().isdigit()
            }

        provider_set: set[int] = set()
        if provider_ids:
            provider_set = {
                int(x)
                for x in provider_ids.split(",")
                if x.strip().isdigit()
            }

        where_clauses: list[str] = []
                # Build parameter mapping for named parameters
        
        # Filter out movies below 7 rating
        where_clauses.append("m.vote_average >= 7")
                
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

        # Build SQL using named parameters so repeated trait params don't require
        # careful positional ordering. Provider placeholders are created as
        # :provider_0, :provider_1, ... and country code is :country_code.
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

            GROUP BY m.id
            HAVING COUNT(r.id) >= {min_reviews}

            ORDER BY score ASC
            LIMIT :limit
        """



        # Add where params into params_map; provider placeholders are named provider_0, provider_1, ...
        if provider_set:
            for i, pid in enumerate(sorted(provider_set)):
                params_map[f"provider_{i}"] = pid
            params_map["country_code"] = country_code

        # If exclude_set is present, add exclude placeholders
        if exclude_set:
            for i, eid in enumerate(sorted(exclude_set)):
                params_map[f"exclude_{i}"] = eid

        logger = logging.getLogger(__name__)

        with CatalogService._connect() as connection:
            # Lower review count requirement if filtering by provider, since that may limit results significantly
            min_reviews = 1 if provider_set else 10
            final_sql = build_query(min_reviews)
            logger.info("recommend: executing query; sql len=%d params=%d", len(final_sql), len(params_map))
            logger.debug("recommend: sql=\n%s", final_sql)
            logger.debug("recommend: params=%r", params_map)

            rows = connection.execute(final_sql, params_map).fetchall()

        items: list[MovieCatalogItem] = []

        for row in rows:
            genres = [g for g in str(row["genres"] or "").split(",") if g]
            items.append(CatalogService._row_to_movie(row, genres=genres))

        return items
    
    
    @staticmethod
    def sharpen_user_profile_old(user, k=8.0, temperature=0.7):
        # 1. strong nonlinear amplification
        sharpened = []
        for t in TRAITS:
            x = user[t]

            # signed exponential sharpening
            if x >= 0:
                z = math.exp(k * x) - 1
            else:
                z = -(math.exp(k * abs(x)) - 1)

            sharpened.append(z)

        # 2. shift to positive space for softmax
        min_z = min(sharpened)
        shifted = [z - min_z for z in sharpened]

        # 3. softmax
        exps = [math.exp(v / temperature) for v in shifted]
        s = sum(exps)

    
    @staticmethod
    def sharpen_user_profile(user, k=8.0, temperature=0.7):
        # 1. strong nonlinear amplification
        values = np.array([user[t] for t in TRAITS])
        min_val = np.min(values)

        max_val = np.max(values)

        range = max_val - min_val

        rescaled = (values - min_val) / range
        return rescaled
        
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
                row = connection.execute(sql, params).fetchone()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No matching movie found for mode={mode}",
                )

            genres = [g for g in str(row["genres"] or "").split(",") if g]
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
        query = """
            SELECT DISTINCT
                provider_id,
                provider_name
            FROM watch_providers
            WHERE UPPER(country_code) = UPPER(?)
        """
        params: list[Any] = [country_code]

        if provider_type:
            query += " AND LOWER(provider_type) = LOWER(?)"
            params.append(provider_type)

        query += " ORDER BY provider_name ASC"

        with CatalogService._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()

        providers: list[WatchProviderItem] = []
        for row in rows:
            providers.append(
                WatchProviderItem(
                    provider_id=int(row["provider_id"]),
                    provider_name=str(row["provider_name"] or "Unknown"),
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
            rows = connection.execute(query, movie_ids).fetchall()

        items: list[MovieCatalogItem] = []
        for row in rows:
            genres = [g for g in str(row["genres"] or "").split(",") if g]
            items.append(CatalogService._row_to_movie(row, genres=genres))

        return items