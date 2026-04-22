"""Recommendation business logic"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.core.config import get_settings
from app.db.models import Recommendation, Movie, Rating, User
from app.services.tmdb_service import TmdbService


POSITIVE_WORDS = {
    "amazing",
    "awesome",
    "beautiful",
    "brilliant",
    "engaging",
    "excellent",
    "favorite",
    "fun",
    "good",
    "great",
    "heartfelt",
    "interesting",
    "love",
    "masterpiece",
    "mind-blowing",
    "moving",
    "powerful",
    "smart",
    "strong",
    "wonderful",
}

NEGATIVE_WORDS = {
    "bad",
    "boring",
    "cheap",
    "confusing",
    "dull",
    "forgettable",
    "hated",
    "messy",
    "predictable",
    "slow",
    "terrible",
    "weak",
    "worst",
}

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "her",
    "his",
    "i",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "we",
    "with",
    "you",
    "your",
}


class RecommendationService:
    """Service for recommendation operations"""

    @staticmethod
    def generate_recommendations(db: Session, user_id: int, limit: int = 10) -> list[Recommendation]:
        """Generate and persist ranked recommendations for a user."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        ratings = db.query(Rating).filter(Rating.user_id == user_id).all()
        if not ratings:
            return []

        watched_movie_ids = {rating.movie_id for rating in ratings}
        watched_movies = (
            db.query(Movie)
            .filter(Movie.id.in_(watched_movie_ids))
            .all()
        )
        watched_tmdb_ids = {movie.tmdb_id for movie in watched_movies if movie.tmdb_id is not None}

        profile = RecommendationService._build_profile(ratings, watched_movies)

        candidates = RecommendationService._build_candidate_pool(
            db,
            watched_movie_ids=watched_movie_ids,
            watched_tmdb_ids=watched_tmdb_ids,
            profile=profile,
            limit=limit,
        )

        scored_candidates = []
        for movie in candidates:
            score, reason = RecommendationService._score_movie(movie, profile)
            if score > 0:
                scored_candidates.append((movie, score, reason))

        scored_candidates.sort(key=lambda item: item[1], reverse=True)

        reranked_candidates = RecommendationService._llm_rerank_candidates(
            scored_candidates=scored_candidates,
            ratings=ratings,
            watched_movies=watched_movies,
            profile=profile,
            limit=limit,
        )
        if reranked_candidates:
            scored_candidates = reranked_candidates

        RecommendationService.delete_old_recommendations(db, user_id)

        recommendations: list[Recommendation] = []
        for movie, score, reason in scored_candidates[:limit]:
            recommendation = Recommendation(
                user_id=user_id,
                movie_id=movie.id,
                score=float(round(score, 4)),
                reason=reason,
            )
            db.add(recommendation)
            recommendations.append(recommendation)

        db.commit()
        for recommendation in recommendations:
            db.refresh(recommendation)

        return recommendations

    @staticmethod
    def _llm_rerank_candidates(
        scored_candidates: list[tuple[Movie, float, str]],
        ratings: list[Rating],
        watched_movies: list[Movie],
        profile: dict,
        limit: int,
    ) -> list[tuple[Movie, float, str]]:
        """Let the LLM choose the final ranking from top candidates."""
        settings = get_settings()
        if not settings.LLM_API_KEY:
            return []

        shortlist = scored_candidates[: max(limit * 3, 20)]
        if not shortlist:
            return []

        movie_by_id = {movie.id: movie for movie in watched_movies}
        watched_lines: list[str] = []
        for rating in ratings[:20]:
            movie = movie_by_id.get(rating.movie_id)
            if not movie:
                continue
            watched_lines.append(
                f"- {movie.title} | score={rating.score}/5 | genres={movie.genre or 'unknown'} | review={rating.review or 'n/a'}"
            )

        candidate_lines: list[str] = []
        for movie, base_score, reason in shortlist:
            candidate_lines.append(
                f"- movie_id={movie.id} | title={movie.title} | genres={movie.genre or 'unknown'} | base_score={base_score:.4f} | overview={movie.description or 'n/a'} | base_reason={reason}"
            )

        summary = profile.get("llm_summary") or ""
        prompt = (
            "You are a movie recommendation ranker. "
            "Choose the best movies for this user from the candidate list. "
            "Use ratings, reviews, genres, and overview context. "
            "Return STRICT JSON only in this exact shape: "
            "{\"ranked\":[{\"movie_id\":123,\"llm_score\":0.0-1.0,\"reason\":\"short reason\"}]}. "
            "Only include movie_ids that appear in candidates. "
            "Prefer diversity and avoid repeating same genre too much.\n\n"
            f"Taste summary: {summary}\n\n"
            "Watched history:\n"
            + "\n".join(watched_lines[:15])
            + "\n\nCandidates:\n"
            + "\n".join(candidate_lines)
        )

        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{settings.LLM_BASE_URL.rstrip('/')}{settings.LLM_CHAT_PATH}"

        try:
            with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            content = RecommendationService._extract_llm_content(response.json())
            parsed = RecommendationService._parse_llm_json(content)
            ranked = parsed.get("ranked", []) if isinstance(parsed, dict) else []
            if not isinstance(ranked, list) or not ranked:
                return []

            base_by_movie_id = {
                movie.id: (movie, score, reason) for movie, score, reason in shortlist
            }
            reranked: list[tuple[Movie, float, str]] = []
            for item in ranked:
                if not isinstance(item, dict):
                    continue
                movie_id = item.get("movie_id")
                if not isinstance(movie_id, int) or movie_id not in base_by_movie_id:
                    continue
                movie, base_score, base_reason = base_by_movie_id[movie_id]
                llm_score_raw = item.get("llm_score", 0.5)
                try:
                    llm_score = max(0.0, min(1.0, float(llm_score_raw)))
                except (TypeError, ValueError):
                    llm_score = 0.5

                combined_score = 0.65 * base_score + 0.35 * llm_score
                llm_reason = str(item.get("reason", "")).strip()
                final_reason = llm_reason if llm_reason else base_reason
                reranked.append((movie, combined_score, final_reason))

            if not reranked:
                return []

            # Keep any non-selected shortlisted items by base score as fallback tail.
            selected_ids = {movie.id for movie, _, _ in reranked}
            tail = [item for item in shortlist if item[0].id not in selected_ids]
            reranked.extend(tail)
            reranked.sort(key=lambda item: item[1], reverse=True)
            return reranked
        except Exception:
            return []

    @staticmethod
    def _build_candidate_pool(
        db: Session,
        watched_movie_ids: set[int],
        watched_tmdb_ids: set[int],
        profile: dict,
        limit: int,
    ) -> list[Movie]:
        """Combine local movies and fresh TMDb discoveries into a single candidate pool."""
        local_candidates = (
            db.query(Movie)
            .filter(Movie.id.notin_(watched_movie_ids))
            .all()
        )

        candidate_movies = {movie.id: movie for movie in local_candidates}

        for tmdb_movie in RecommendationService._discover_tmdb_candidates(profile):
            if tmdb_movie.id in watched_tmdb_ids:
                continue

            existing = db.query(Movie).filter(Movie.tmdb_id == tmdb_movie.id).first()
            if existing and existing.id in watched_movie_ids:
                continue
            if existing:
                candidate_movies[existing.id] = existing
                continue

            imported = TmdbService.import_movie_sync(db, tmdb_movie.id)
            candidate_movies[imported.id] = imported

        return list(candidate_movies.values())[: max(limit * 5, limit)]

    @staticmethod
    def _discover_tmdb_candidates(profile: dict) -> list:
        """Discover fresh movies from TMDb using the user's favorite genres."""
        genre_names = [name for name, _score in profile["genre_weights"].most_common(5)]
        if not genre_names:
            discover = TmdbService.discover_movies(genre_ids=None)
            return discover.results

        genre_map = TmdbService.get_genre_map()
        genre_ids = [genre_map[name] for name in genre_names if name in genre_map]
        if not genre_ids:
            discover = TmdbService.discover_movies(genre_ids=None)
            return discover.results

        discover = TmdbService.discover_movies(genre_ids=genre_ids)
        return discover.results

    @staticmethod
    def get_recommendations_for_user(
        db: Session, user_id: int, limit: int = 10
    ) -> list[Recommendation]:
        """Get recommendations for a user"""
        return (
            db.query(Recommendation)
            .filter(Recommendation.user_id == user_id)
            .order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_recommendation_items_for_user(
        db: Session, user_id: int, limit: int = 10
    ) -> list[tuple[Recommendation, Movie]]:
        """Get recommendation rows together with their associated movie records."""
        recommendations = RecommendationService.get_recommendations_for_user(
            db, user_id, limit
        )
        return [(recommendation, recommendation.movie) for recommendation in recommendations if recommendation.movie]

    @staticmethod
    def _build_profile(ratings: list[Rating], watched_movies: list[Movie]) -> dict:
        """Create a compact user taste profile from watched movies and reviews."""
        genre_weights = Counter()
        keyword_weights = Counter()
        positive_reference_count = 0
        negative_reference_count = 0
        recency_weights = {}

        movie_by_id = {movie.id: movie for movie in watched_movies}

        for rating in ratings:
            movie = movie_by_id.get(rating.movie_id)
            if not movie:
                continue

            weight = RecommendationService._rating_weight(rating.score)
            if movie.genre:
                for genre in RecommendationService._split_genres(movie.genre):
                    genre_weights[genre] += weight

            review_sentiment = RecommendationService._sentiment_score(rating.review or "")
            if review_sentiment >= 0:
                positive_reference_count += 1
            else:
                negative_reference_count += 1

            for token in RecommendationService._tokenize(f"{movie.title} {movie.description or ''} {rating.review or ''}"):
                keyword_weights[token] += weight * (1.0 + review_sentiment)

            recency_weights[movie.id] = RecommendationService._recency_weight(rating.created_at)

        llm_profile = RecommendationService._extract_taste_profile_with_llm(ratings, watched_movies)
        for genre in llm_profile.get("preferred_genres", []):
            genre_weights[genre] += 1.5
        for genre in llm_profile.get("disliked_genres", []):
            genre_weights[genre] -= 0.75
        for theme in llm_profile.get("themes", []):
            for token in RecommendationService._tokenize(theme):
                keyword_weights[token] += 1.25

        return {
            "genre_weights": genre_weights,
            "keyword_weights": keyword_weights,
            "positive_reference_count": positive_reference_count,
            "negative_reference_count": negative_reference_count,
            "recency_weights": recency_weights,
            "llm_summary": llm_profile.get("summary"),
            "llm_themes": llm_profile.get("themes", []),
        }

    @staticmethod
    def _score_movie(movie: Movie, profile: dict) -> tuple[float, str]:
        """Score a candidate movie against the user's taste profile."""
        genre_similarity = 0.0
        text_similarity = 0.0
        popularity_score = RecommendationService._normalize(movie.average_rating, 0.0, 5.0)

        candidate_tokens = Counter(
            RecommendationService._tokenize(f"{movie.title} {movie.description or ''}")
        )
        candidate_genres = RecommendationService._split_genres(movie.genre or "")

        for genre in candidate_genres:
            genre_similarity += profile["genre_weights"].get(genre, 0.0)

        for token, count in candidate_tokens.items():
            text_similarity += profile["keyword_weights"].get(token, 0.0) * min(count, 1)

        genre_similarity = RecommendationService._normalize(genre_similarity, 0.0, 12.0)
        text_similarity = RecommendationService._normalize(text_similarity, 0.0, 18.0)
        popularity_score = RecommendationService._normalize(popularity_score, 0.0, 1.0)

        rating_affinity = 0.0
        if movie.average_rating:
            rating_affinity = RecommendationService._normalize(movie.average_rating, 0.0, 5.0)

        recency_weight = 0.0
        if movie.id in profile["recency_weights"]:
            recency_weight = profile["recency_weights"][movie.id]

        final_score = (
            0.38 * genre_similarity
            + 0.28 * text_similarity
            + 0.18 * rating_affinity
            + 0.10 * popularity_score
            + 0.06 * recency_weight
        )

        reasons = []
        if genre_similarity >= 0.25 and candidate_genres:
            reasons.append(f"shares genres like {candidate_genres[0]}")
        if text_similarity >= 0.2:
            reasons.append("matches words from your liked reviews")
        if rating_affinity >= 0.65:
            reasons.append("has strong overall movie ratings")
        if profile.get("llm_themes"):
            matched_themes = [
                theme
                for theme in profile["llm_themes"]
                if any(token in RecommendationService._tokenize(f"{movie.title} {movie.description or ''}") for token in RecommendationService._tokenize(theme))
            ]
            if matched_themes:
                reasons.append(f"matches themes like {matched_themes[0]}")

        if not reasons and profile.get("llm_summary"):
            reasons.append(profile["llm_summary"])

        reason = "Recommended because it " + ", ".join(reasons) if reasons else "Recommended based on your watch history"
        return final_score, reason

    @staticmethod
    def _extract_taste_profile_with_llm(ratings: list[Rating], watched_movies: list[Movie]) -> dict:
        """Use the LLM to summarize review themes and genre preferences."""
        sample_items: list[str] = []
        movie_by_id = {movie.id: movie for movie in watched_movies}

        for rating in ratings:
            if not rating.review:
                continue
            movie = movie_by_id.get(rating.movie_id)
            if not movie:
                continue
            sample_items.append(
                f"Title: {movie.title}\nGenres: {movie.genre or 'unknown'}\nRating: {rating.score}/5\nReview: {rating.review}"
            )

        if not sample_items:
            return {}

        settings = get_settings()
        if not settings.LLM_API_KEY:
            return {}

        prompt = (
            "You are helping a movie recommender understand the user's taste. "
            "Read the examples and return STRICT JSON only with these keys: "
            "preferred_genres (array of lowercase genre names), "
            "disliked_genres (array of lowercase genre names), "
            "themes (array of short lowercase theme phrases), "
            "summary (single short sentence). "
            "Do not include markdown or extra text.\n\n"
            + "\n\n".join(sample_items[:5])
        )

        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{settings.LLM_BASE_URL.rstrip('/')}{settings.LLM_CHAT_PATH}"

        try:
            with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            content = RecommendationService._extract_llm_content(response.json())
            parsed = RecommendationService._parse_llm_json(content)
            if not isinstance(parsed, dict):
                return {}
            return {
                "preferred_genres": [str(item).strip().lower() for item in parsed.get("preferred_genres", []) if str(item).strip()],
                "disliked_genres": [str(item).strip().lower() for item in parsed.get("disliked_genres", []) if str(item).strip()],
                "themes": [str(item).strip().lower() for item in parsed.get("themes", []) if str(item).strip()],
                "summary": str(parsed.get("summary", "")).strip(),
            }
        except Exception:
            return {}

    @staticmethod
    def _extract_llm_content(data: dict) -> str:
        """Extract assistant content from an OpenAI-compatible response."""
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            pieces: list[str] = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    pieces.append(str(part.get("text", "")))
                elif isinstance(part, str):
                    pieces.append(part)
            return "\n".join(pieces).strip()
        return json.dumps(content)

    @staticmethod
    def _parse_llm_json(content: str):
        """Parse JSON even if the model wrapped it in code fences."""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.removeprefix("json").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {}

    @staticmethod
    def _split_genres(genre_text: str) -> list[str]:
        return [genre.strip().lower() for genre in genre_text.split(",") if genre.strip()]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [
            token
            for token in re.findall(r"[a-z0-9']+", text.lower())
            if token not in STOP_WORDS and len(token) > 2
        ]

    @staticmethod
    def _sentiment_score(review_text: str) -> float:
        tokens = RecommendationService._tokenize(review_text)
        if not tokens:
            return 0.0

        positive = sum(1 for token in tokens if token in POSITIVE_WORDS)
        negative = sum(1 for token in tokens if token in NEGATIVE_WORDS)
        return (positive - negative) / max(len(tokens), 1)

    @staticmethod
    def _rating_weight(score: float) -> float:
        return max(0.0, min(1.0, (score - 2.0) / 3.0))

    @staticmethod
    def _recency_weight(created_at: datetime | None) -> float:
        if not created_at:
            return 0.0

        now = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = max((now - created_at).days, 0)
        return max(0.0, 1.0 - min(age_days, 365) / 365.0)

    @staticmethod
    def _normalize(value: float, min_value: float, max_value: float) -> float:
        if max_value <= min_value:
            return 0.0
        return max(0.0, min(1.0, (value - min_value) / (max_value - min_value)))

    @staticmethod
    def delete_old_recommendations(db: Session, user_id: int) -> int:
        """Delete existing recommendations for a user"""
        count = (
            db.query(Recommendation).filter(Recommendation.user_id == user_id).delete()
        )
        db.commit()
        return count
