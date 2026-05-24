"""Import TMDb movie data into the local catalog SQLite database."""
from __future__ import annotations

import logging
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.config import get_settings


logger = logging.getLogger("uvicorn.error")


prototypes: dict[str, dict[str, list[str]]] = {
    "Wisdom": {
        "Creativity": [
            "Characters who invent, imagine, innovate, or approach problems in original and meaningful ways.",
            "Finding original solutions to difficult problems.",
            "Expressing originality, imagination, or innovation.",
        ],
        "Curiosity": [
            "Characters driven to explore, discover, or understand unfamiliar people, places, or ideas.",
            "Seeking new experiences and unfamiliar situations.",
            "Exploring and discovering the unknown.",
        ],
        "Love of Learning": [
            "Characters strongly motivated to gain knowledge, master skills, or deepen understanding.",
            "Acquiring new levels of knowledge.",
            "Being deeply motivated to learn, grow, and expand one's understanding.",
            "Studying, researching, and acquiring expertise.",
            "Reading, learning new skills, expanding intellectual capacity.",
        ],
        "Judgment": [
            "Analyzing facts and reasoning through complex situations.",
            "Evaluating evidence before making decisions.",
            "Using logic and critical thinking to solve problems.",
            "Examining different viewpoints and weighing information.",
            "Making sound decisions based on careful analysis.",
        ],
        "Perspective": [
            "Teaching others from experience and knowledge.",
            "Offering practical advice rooted in understanding.",
            "Sharing knowledge and expertise with others.",
            "Guiding others through lessons learned from experience.",
            "Imparting wisdom through mentorship and instruction.",
        ],
    },
    "Courage": {
        "Bravery": [
            "Characters who act on their convictions, and face threats, challenges, and pains, despite doubts and fears.",
            "Valuing a goal or conviction and acting upon it, whether popular or not.",
            "Speaking up for what's right, even if it's unfavorable to a group.",
            "Facing painful aspect of oneself.",
            "Putting their own life at risk for the greater good.",
            "Protecting others despite personal danger.",
        ],
        "Honesty": [
            "Characters who are honest to themselves and others.",
            "Characters present themselves and their reactions accurately to others.",
            "Taking responsibility for own feelings and actions.",
            "Being authentic and sincere without pretense.",
            "Being true to yourself.",
        ],
        "Perseverance": [
            "Characters persist toward their goals despite obstacles, discouragements, or disappointments.",
            "Working hard and finishing what was started despite barriers and obstacles that arise.",
            "Overcoming thoughts of giving up.",
            "Following through on commitments.",
        ],
        "Zest": [
            "Characters who feel vital and full of energy.",
            "Characters who approach life feeling activated and enthusiastic.",
            "Engaging with life enthusiastically and energetically.",
            "Bringing vitality and excitement to everyday situations.",
        ],
    },
    "Humanity": {
        "Kindness": [
            "Characters who are helpful and empathic and regularly do nice favors for others without expecting anything in return.",
            "Being generous with others.",
            "Giving time, money, and talent to support those who are in need.",
            "Giving attention and affirmation to others without a sense of duty or principle.",
            "Being nice to others.",
        ],
        "Love": [
            "Valueing close relationships with others.",
            "Experiencing close, loving relationships that are characterized by giving and receiving love, warmth, and caring.",
            "Developing meaningful friendship.",
            "Developing meaningful relationships.",
            "Experiencing romance with someone or being in love with someone.",
            "Developing meaningful attachment.",
            "The willingness to accept love from others.",
            "The willingness to love others.",
        ],
        "Social Intelligence": [
            "Characters who are aware of and understand their own feelings and thoughts, as well as the feelings of those around them.",
            "Awareness of the motives and feelings of others.",
            "Awareness of one's own feelings and motives.",
            "Understanding and adapting to different social situations.",
        ],
    },
    "Justice": {
        "Fairness": [
            "Characters who treat everyone equally and fairly.",
            "Characters who give everyone the same chance.",
            "Characters who apply the same rules to everyone.",
            "Equal opportunity for all.",
            "Treating people justly.",
            "Determining moral rights and responsibilities.",
            "Characters who are able to put themselves in the shoes of others.",
            "Legal and moral behaviour.",
            "Treating people impartially regardless of personal bias.",
            "Confronting corruption and injustice.",
            "Recognizing and resisting unfair treatment.",
            "Exposing immoral systems or abuse of power.",
        ],
        "Leadership": [
            "Characters who take charge and guide groups to meaningful goals.",
            "Characters who ensure good relations among group members.",
            "Organizing and encouraging a group.",
            "Setting goals and accomplishing goals.",
            "Providing a vision or message.",
            "Inspiring and empowering others",
        ],
        "Teamwork": [
            "Characters who are helpful and a contributing group and team member.",
            "Characters who feel responsible for helping the team reach its goals.",
            "Working together.",
            "Characters who are dedicated member of a group or community",
            "Helping family or friends.",
            "Responsibility toward one's own community.",
            "Loyalty to a group.",
            "Loyalty to one's homeland without hostility toward other nations.",
        ],
    },
    "Temperance": {
        "Forgiveness": [
            "Characters who forgive others when they upset them or behaved badly towards them.",
            "Understanding towards those who have wronged or hurt us.",
            "Letting go frustration, disappointment, resentment, or other painful feelings associated with offense.",
            "Giving mercy.",
            "Accepting the shortcomings, flaws, and imperfections of others.",
            "Giving second chances.",
            "Letting go of guilt and anger.",
        ],
        "Humility": [
            "Characters who are not seeking to be the center of attention or to receive recognition.",
            "Characters who are aware of their own strengths and talents, but are humble.",
            "Characters who accurately evaluate their accomplishments.",
            "Self-assessment, recognition of limitations, and keeping accomplishments in perspective.",
            "Forgetting of the self.",
            "Allowing actions and accomplishments to speak for themselves.",
        ],
        "Prudence": [
            "Characters who act carefully and cautiously, looking to avoid unnecessary risks.",
            "Characters who plan with the future in mind.",
            "Characters who think before acting and make decisions carefully.",
            "Characters who consider the long-term consequences of their actions.",
            "Making positive choices that lead to meaningful goals and avoid regret.",
            "Discerning the right path and deciding how to act in the face of uncertainty or fear.",
        ],
        "Self-Regulation": [
            "Characters who manage their feelings and actions and who are disciplined and self-controlled.",
            "Controlling appetites and emotions.",
            "Controlling reactions to disappointment and insecurities.",
            "Keeping a sense of balance and order, even when circumstances are difficult.",
            "Keeping composure in tense situations.",
        ],
    },
    "Transcendence": {
        "Appreciation of Beauty & Excellence": [
            "Recognizing and admiring beauty in nature, art, and the world.",
            "Being moved by natural beauty or artistic expression.",
            "Appreciating excellence and skill in craftsmanship or performance.",
            "Experiencing awe at the beauty of the natural world.",
            "Drawn to aesthetic experience and artistic inspiration.",
            "Moved to tears or wonder by beauty.",
        ],
        "Gratitude": [
            "Expressing deep thankfulness and appreciation.",
            "Recognizing the gifts and kindnesses received.",
            "Showing genuine appreciation for what one has.",
            "Feeling blessed and grateful for life's moments.",
            "Acknowledging and celebrating goodness received from others.",
        ],
        "Hope": [
            "Maintaining optimism despite hardship or uncertainty.",
            "Believing in a better future even when facing difficulties.",
            "Trusting that things will improve or work out.",
            "Showing resilience and positive expectation for what's to come.",
            "Persisting with faith that goals will be achieved.",
        ],
        "Humor": [
            "Characters who approach life playfully, making others laugh, and finding humor in difficult and stressful times.",
            "Recognizing what is amusing in situations.",
            "Being able to laugh about situations even when it is a difficult or stressful situation.",
            "Making people smile or laugh.",
            "Keeping a cheerful view on adversity.",
            "Sustaining a good mood in a state of seriousness.",
            "Being able to offer the lighter side to others.",
        ],
        "Spirituality": [
            "Having explicit spiritual or religious faith and practice.",
            "Characters motivated by religious belief or spiritual connection.",
            "Seeking connection to the divine or sacred.",
            "Practicing faith rituals or spiritual disciplines.",
            "Drawing strength and meaning from spiritual beliefs.",
            "Religious conviction guiding character's choices.",
            "Quest for spiritual enlightenment or higher purpose beyond material concerns.",
        ],
    },
}


class CatalogImportService:
    """Fetch, score, and persist TMDb movie data into the local catalog."""

    @staticmethod
    def _settings():
        return get_settings()

    @staticmethod
    def _db_path() -> Path:
        settings = CatalogImportService._settings()
        backend_root = Path(__file__).resolve().parents[2]
        path = Path(settings.MOVIES_DB_PATH).expanduser()
        if not path.is_absolute():
            path = backend_root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _connect() -> sqlite3.Connection:
        connection = sqlite3.connect(CatalogImportService._db_path(), timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @staticmethod
    def ensure_schema() -> None:
        with CatalogImportService._connect() as connection:
            connection.execute("PRAGMA busy_timeout = 30000")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    summary TEXT,
                    image_url TEXT,
                    vote_average REAL,
                    release_date TEXT,
                    adult INTEGER
                );

                CREATE TABLE IF NOT EXISTS genres (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE
                );

                CREATE TABLE IF NOT EXISTS movie_genres (
                    movie_id INTEGER,
                    genre_id INTEGER,
                    PRIMARY KEY (movie_id, genre_id)
                );

                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE
                );

                CREATE TABLE IF NOT EXISTS movie_keywords (
                    movie_id INTEGER,
                    keyword_id INTEGER,
                    PRIMARY KEY (movie_id, keyword_id)
                );

                CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    profile_path TEXT,
                    known_for_department TEXT
                );

                CREATE TABLE IF NOT EXISTS movie_people (
                    movie_id INTEGER,
                    person_id INTEGER,
                    credit_type TEXT,
                    role_name TEXT,
                    credit_order INTEGER,
                    PRIMARY KEY (movie_id, person_id, credit_type, role_name)
                );

                CREATE TABLE IF NOT EXISTS similar_movies (
                    movie_id INTEGER,
                    similar_movie_id INTEGER,
                    title TEXT,
                    overview TEXT,
                    poster_path TEXT,
                    PRIMARY KEY (movie_id, similar_movie_id)
                );

                CREATE TABLE IF NOT EXISTS recommended_movies (
                    movie_id INTEGER,
                    recommended_movie_id INTEGER,
                    title TEXT,
                    overview TEXT,
                    poster_path TEXT,
                    PRIMARY KEY (movie_id, recommended_movie_id)
                );

                CREATE TABLE IF NOT EXISTS watch_providers (
                    movie_id INTEGER,
                    country_code TEXT,
                    provider_type TEXT,
                    provider_id INTEGER,
                    provider_name TEXT,
                    logo_path TEXT,
                    link TEXT,
                    PRIMARY KEY (movie_id, country_code, provider_type, provider_id)
                );

                CREATE TABLE IF NOT EXISTS spoken_languages (
                    iso_639_1 TEXT PRIMARY KEY,
                    english_name TEXT,
                    name TEXT
                );

                CREATE TABLE IF NOT EXISTS movie_spoken_languages (
                    movie_id INTEGER,
                    language_code TEXT,
                    PRIMARY KEY (movie_id, language_code)
                );

                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    movie_id INTEGER,
                    review_text TEXT,
                    author TEXT
                );

                CREATE TABLE IF NOT EXISTS processed_pages (
                    year INTEGER,
                    page INTEGER,
                    PRIMARY KEY (year, page)
                );

                CREATE TABLE IF NOT EXISTS movie_virtue_scores_wide (
                    movie_id INTEGER,
                    Wisdom REAL,
                    Courage REAL,
                    Humanity REAL,
                    Justice REAL,
                    Temperance REAL,
                    Transcendence REAL
                );
                """
            )

    @staticmethod
    def _tmdb_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        settings = CatalogImportService._settings()
        if not settings.TMDB_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TMDb API key is not configured on the backend.",
            )

        import requests

        request_params = {"api_key": settings.TMDB_API_KEY}
        if params:
            request_params.update(params)

        try:
            response = requests.get(
                f"{settings.TMDB_BASE_URL.rstrip('/')}{path}",
                params=request_params,
                timeout=settings.TMDB_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"TMDb request failed for {path}: {exc}",
            ) from exc

        return response.json()

    @staticmethod
    def fetch_movie_details(tmdb_movie_id: int) -> dict[str, Any]:
        return CatalogImportService._tmdb_get(f"/movie/{tmdb_movie_id}", {"language": "en-US"})

    @staticmethod
    def fetch_keywords(tmdb_movie_id: int) -> list[dict[str, Any]]:
        return CatalogImportService._tmdb_get(f"/movie/{tmdb_movie_id}/keywords").get("keywords", [])

    @staticmethod
    def fetch_credits(tmdb_movie_id: int) -> dict[str, Any]:
        return CatalogImportService._tmdb_get(f"/movie/{tmdb_movie_id}/credits")

    @staticmethod
    def fetch_similar_movies(tmdb_movie_id: int) -> list[dict[str, Any]]:
        return CatalogImportService._tmdb_get(f"/movie/{tmdb_movie_id}/similar").get("results", [])

    @staticmethod
    def fetch_recommendations(tmdb_movie_id: int) -> list[dict[str, Any]]:
        return CatalogImportService._tmdb_get(f"/movie/{tmdb_movie_id}/recommendations").get("results", [])

    @staticmethod
    def fetch_watch_providers(tmdb_movie_id: int) -> dict[str, Any]:
        return CatalogImportService._tmdb_get(f"/movie/{tmdb_movie_id}/watch/providers").get("results", {})

    @staticmethod
    def fetch_reviews(tmdb_movie_id: int) -> list[dict[str, Any]]:
        return CatalogImportService._tmdb_get(f"/movie/{tmdb_movie_id}/reviews").get("results", [])

    @staticmethod
    def store_genres(connection: sqlite3.Connection, movie_id: int, genres: list[dict[str, Any]]) -> None:
        for genre in genres:
            genre_id = genre.get("id")
            if genre_id is None:
                continue
            connection.execute(
                "INSERT OR IGNORE INTO genres (id, name) VALUES (?, ?)",
                (genre_id, genre.get("name")),
            )
            connection.execute(
                "INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
                (movie_id, genre_id),
            )

    @staticmethod
    def store_keywords(connection: sqlite3.Connection, movie_id: int, keywords: list[dict[str, Any]]) -> None:
        for keyword in keywords:
            keyword_id = keyword.get("id")
            if keyword_id is None:
                continue
            connection.execute(
                "INSERT OR IGNORE INTO keywords (id, name) VALUES (?, ?)",
                (keyword_id, keyword.get("name")),
            )
            connection.execute(
                "INSERT OR IGNORE INTO movie_keywords (movie_id, keyword_id) VALUES (?, ?)",
                (movie_id, keyword_id),
            )

    @staticmethod
    def store_people(connection: sqlite3.Connection, movie_id: int, credits: dict[str, Any]) -> None:
        for person in credits.get("cast", [])[:10]:
            connection.execute(
                "INSERT OR IGNORE INTO people (id, name, profile_path, known_for_department) VALUES (?, ?, ?, ?)",
                (person["id"], person.get("name"), person.get("profile_path"), person.get("known_for_department")),
            )
            connection.execute(
                "INSERT OR IGNORE INTO movie_people (movie_id, person_id, credit_type, role_name, credit_order) VALUES (?, ?, ?, ?, ?)",
                (movie_id, person["id"], "cast", person.get("character"), person.get("order")),
            )

        for person in credits.get("crew", [])[:10]:
            connection.execute(
                "INSERT OR IGNORE INTO people (id, name, profile_path, known_for_department) VALUES (?, ?, ?, ?)",
                (person["id"], person.get("name"), person.get("profile_path"), person.get("known_for_department")),
            )
            connection.execute(
                "INSERT OR IGNORE INTO movie_people (movie_id, person_id, credit_type, role_name, credit_order) VALUES (?, ?, ?, ?, ?)",
                (movie_id, person["id"], "crew", person.get("job"), person.get("order")),
            )

    @staticmethod
    def store_related_movies(
        connection: sqlite3.Connection,
        movie_id: int,
        rows: list[dict[str, Any]],
        table_name: str,
        id_column: str,
    ) -> None:
        for related in rows[:10]:
            related_id = related.get("id")
            if related_id is None:
                continue
            connection.execute(
                f"INSERT OR IGNORE INTO {table_name} (movie_id, {id_column}, title, overview, poster_path) VALUES (?, ?, ?, ?, ?)",
                (movie_id, related_id, related.get("title"), related.get("overview"), related.get("poster_path")),
            )

    @staticmethod
    def store_watch_providers(
        connection: sqlite3.Connection,
        movie_id: int,
        providers_by_country: dict[str, Any],
    ) -> None:
        for country_code, provider_groups in providers_by_country.items():
            for provider_type in ("flatrate", "rent", "buy", "ads", "free"):
                for provider in provider_groups.get(provider_type, []):
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO watch_providers (
                            movie_id, country_code, provider_type, provider_id, provider_name, logo_path, link
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            movie_id,
                            country_code,
                            provider_type,
                            provider["provider_id"],
                            provider.get("provider_name"),
                            provider.get("logo_path"),
                            provider_groups.get("link"),
                        ),
                    )

    @staticmethod
    def store_spoken_languages(connection: sqlite3.Connection, movie_id: int, languages: list[dict[str, Any]]) -> None:
        for language in languages:
            language_code = language.get("iso_639_1")
            if not language_code:
                continue
            connection.execute(
                "INSERT OR IGNORE INTO spoken_languages (iso_639_1, english_name, name) VALUES (?, ?, ?)",
                (language_code, language.get("english_name"), language.get("name")),
            )
            connection.execute(
                "INSERT OR IGNORE INTO movie_spoken_languages (movie_id, language_code) VALUES (?, ?)",
                (movie_id, language_code),
            )

    @staticmethod
    def store_reviews(connection: sqlite3.Connection, movie_id: int, reviews: list[dict[str, Any]]) -> None:
        for review in reviews[:2]:
            if not review.get("id"):
                continue
            connection.execute(
                "INSERT OR IGNORE INTO reviews (id, movie_id, review_text, author) VALUES (?, ?, ?, ?)",
                (review["id"], movie_id, review.get("content"), review.get("author")),
            )

    @staticmethod
    def save_movie_and_related_data(connection: sqlite3.Connection, movie_id: int, title: str, summary: str, details: dict[str, Any]) -> None:
        image_url = None
        if details.get("poster_path"):
            image_url = f"https://image.tmdb.org/t/p/w500{details['poster_path']}"

        logger.info("Saving movie %s (%s) to local catalog", movie_id, title)
        connection.execute(
            """
            INSERT OR REPLACE INTO movies (
                id, title, summary, image_url, vote_average, release_date, adult
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                movie_id,
                title,
                summary,
                image_url,
                details.get("vote_average"),
                details.get("release_date"),
                1 if details.get("adult", False) else 0,
            ),
        )
        logger.info("Saved movie %s to local catalog", movie_id)

    @staticmethod
    @lru_cache(maxsize=1)
    def _model():
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-MiniLM-L6-v2")

    @staticmethod
    @lru_cache(maxsize=1)
    def _prototype_embeddings() -> dict[str, dict[str, Any]]:
        model = CatalogImportService._model()
        embeddings: dict[str, dict[str, Any]] = {}

        for virtue, substrengths in prototypes.items():
            embeddings[virtue] = {}
            for substrength, sentences in substrengths.items():
                embeddings[virtue][substrength] = model.encode(
                    sentences,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                )

        return embeddings

    @staticmethod
    def score_movie_summary(summary: str) -> dict[str, Any]:
        if not summary or not summary.strip():
            return {
                virtue: {
                    "score": 0.0,
                    "substrengths": {substrength: 0.0 for substrength in substrengths},
                }
                for virtue, substrengths in prototypes.items()
            }

        model = CatalogImportService._model()
        movie_vector = model.encode([summary], convert_to_numpy=True, normalize_embeddings=True)[0]

        from sklearn.metrics.pairwise import cosine_similarity

        results: dict[str, Any] = {}
        for virtue, substrengths in CatalogImportService._prototype_embeddings().items():
            substrength_scores: dict[str, float] = {}
            for substrength, proto_vectors in substrengths.items():
                similarities = cosine_similarity([movie_vector], proto_vectors)[0]
                substrength_scores[substrength] = float(sum(similarities) / len(similarities)) if len(similarities) else 0.0

            results[virtue] = {
                "score": float(sum(substrength_scores.values()) / len(substrength_scores)) if substrength_scores else 0.0,
                "substrengths": substrength_scores,
            }

        return results

    @staticmethod
    def save_virtue_scores(connection: sqlite3.Connection, movie_id: int, scores: dict[str, Any]) -> None:
        existing = connection.execute(
            """
            SELECT 1
            FROM movie_virtue_scores_wide
            WHERE movie_id = ?
            LIMIT 1
            """,
            (movie_id,),
        ).fetchone()

        if existing is not None:
            logger.info("Skipping virtue-score insert for movie %s because scores already exist", movie_id)
            return

        logger.info("Saving virtue scores for movie %s to local catalog", movie_id)
        connection.execute(
            """
            INSERT INTO movie_virtue_scores_wide (
                movie_id, Wisdom, Courage, Humanity, Justice, Temperance, Transcendence
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                movie_id,
                scores["Wisdom"]["score"],
                scores["Courage"]["score"],
                scores["Humanity"]["score"],
                scores["Justice"]["score"],
                scores["Temperance"]["score"],
                scores["Transcendence"]["score"],
            ),
        )
        logger.info("Saved virtue scores for movie %s to local catalog", movie_id)

    @staticmethod
    def import_movie(tmdb_movie_id: int) -> dict[str, Any]:
        """Fetch a TMDb movie, persist it locally, and compute virtue scores."""

        CatalogImportService.ensure_schema()

        details = CatalogImportService.fetch_movie_details(tmdb_movie_id)
        title = details.get("title") or details.get("original_title") or "Untitled"
        summary = details.get("overview") or ""
        logger.info("Importing TMDb movie %s (%s)", tmdb_movie_id, title)

        with CatalogImportService._connect() as connection:
            CatalogImportService.save_movie_and_related_data(connection, tmdb_movie_id, title, summary, details)
            CatalogImportService.store_genres(connection, tmdb_movie_id, details.get("genres", []))
            CatalogImportService.store_keywords(connection, tmdb_movie_id, CatalogImportService.fetch_keywords(tmdb_movie_id))
            CatalogImportService.store_people(connection, tmdb_movie_id, CatalogImportService.fetch_credits(tmdb_movie_id))
            CatalogImportService.store_related_movies(
                connection,
                tmdb_movie_id,
                CatalogImportService.fetch_similar_movies(tmdb_movie_id),
                "similar_movies",
                "similar_movie_id",
            )
            CatalogImportService.store_related_movies(
                connection,
                tmdb_movie_id,
                CatalogImportService.fetch_recommendations(tmdb_movie_id),
                "recommended_movies",
                "recommended_movie_id",
            )
            CatalogImportService.store_watch_providers(
                connection,
                tmdb_movie_id,
                CatalogImportService.fetch_watch_providers(tmdb_movie_id),
            )
            CatalogImportService.store_spoken_languages(connection, tmdb_movie_id, details.get("spoken_languages", []))
            CatalogImportService.store_reviews(connection, tmdb_movie_id, CatalogImportService.fetch_reviews(tmdb_movie_id))

            existing_scores = connection.execute(
                """
                SELECT Wisdom, Courage, Humanity, Justice, Temperance, Transcendence
                FROM movie_virtue_scores_wide
                WHERE movie_id = ?
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (tmdb_movie_id,),
            ).fetchone()

            if existing_scores is None:
                scores = CatalogImportService.score_movie_summary(summary)
                CatalogImportService.save_virtue_scores(connection, tmdb_movie_id, scores)
            else:
                scores = {
                    "Wisdom": {"score": float(existing_scores["Wisdom"] or 0.0), "substrengths": {}},
                    "Courage": {"score": float(existing_scores["Courage"] or 0.0), "substrengths": {}},
                    "Humanity": {"score": float(existing_scores["Humanity"] or 0.0), "substrengths": {}},
                    "Justice": {"score": float(existing_scores["Justice"] or 0.0), "substrengths": {}},
                    "Temperance": {"score": float(existing_scores["Temperance"] or 0.0), "substrengths": {}},
                    "Transcendence": {"score": float(existing_scores["Transcendence"] or 0.0), "substrengths": {}},
                }

            logger.info("Finished importing TMDb movie %s (%s)", tmdb_movie_id, title)
        return {
            "movie_id": tmdb_movie_id,
            "title": title,
            "summary": summary,
            "scores": scores,
        }