"""Service for external LLM chat completion calls"""
import json
import logging

import httpx
from fastapi import HTTPException, status
from sqlmodel import Session

from app.db.models import Movie, Rating, Recommendation, User
from app.core.config import get_settings
from app.schemas.chat import ChatRequest, ChatResponse


# Use uvicorn's configured logger so INFO lines are visible in container logs.
logger = logging.getLogger("uvicorn.error")


class ChatService:
    """Calls Open WebUI/OpenAI-compatible chat completion APIs"""

    @staticmethod
    async def create_completion(chat_in: ChatRequest, db: Session) -> ChatResponse:
        settings = get_settings()

        if not settings.LLM_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "LLM_API_KEY is not configured on the backend. "
                    "Set it in backend/.env."
                ),
            )

        model = chat_in.model or settings.LLM_MODEL
        url = f"{settings.LLM_BASE_URL.rstrip('/')}{settings.LLM_CHAT_PATH}"

        messages: list[dict[str, str]] = []
        if chat_in.user_id is not None:
            user_context = ChatService._build_user_movie_context(db, chat_in.user_id)
            if user_context:
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "Use this user profile context to personalize movie advice. "
                            "If context conflicts with user prompt, prioritize the prompt.\n\n"
                            f"{user_context}"
                        ),
                    }
                )

        messages.append({"role": "user", "content": chat_in.message})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": chat_in.temperature,
            "stream": False,
        }
        if chat_in.max_tokens is not None:
            payload["max_tokens"] = chat_in.max_tokens

        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }

        logger.info(
            "Sending LLM chat completion request to %s with payload: %s",
            url,
            json.dumps(payload),
        )

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upstream LLM request failed: {detail}",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not reach LLM server: {exc}",
            ) from exc

        data = response.json()
        content = ChatService._extract_content(data)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="LLM response did not contain message content.",
            )

        return ChatResponse(reply=content, model=model)

    @staticmethod
    def _extract_content(data: dict) -> str:
        """Extract text content from OpenAI-compatible response bodies"""
        choices = data.get("choices")
        if not choices:
            return ""

        message = choices[0].get("message", {})
        content = message.get("content", "")

        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(str(part.get("text", "")))
                elif isinstance(part, str):
                    text_parts.append(part)
            return "\n".join([p for p in text_parts if p]).strip()

        if isinstance(content, str):
            return content.strip()

        return json.dumps(content).strip() if content else ""

    @staticmethod
    def _build_user_movie_context(db: Session, user_id: int) -> str:
        """Build concise profile context from watched, ratings, reviews, and recommendations."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return ""

        ratings = (
            db.query(Rating, Movie)
            .join(Movie, Movie.id == Rating.movie_id)
            .filter(Rating.user_id == user_id)
            .order_by(Rating.updated_at.desc())
            .limit(15)
            .all()
        )

        recommendations = (
            db.query(Recommendation, Movie)
            .join(Movie, Movie.id == Recommendation.movie_id)
            .filter(Recommendation.user_id == user_id)
            .order_by(Recommendation.score.desc())
            .limit(10)
            .all()
        )

        if not ratings and not recommendations:
            return (
                f"User: {user.username} (id={user.id})\n"
                "No ratings or recommendation history yet."
            )

        lines = [f"User: {user.username} (id={user.id})"]

        if ratings:
            lines.append("Recent ratings:")
            for rating, movie in ratings:
                review_preview = (rating.review or "").strip()
                if len(review_preview) > 120:
                    review_preview = review_preview[:117] + "..."
                lines.append(
                    f"- {movie.title} | score={rating.score}/5 | genres={movie.genre or 'unknown'}"
                    + (f" | review={review_preview}" if review_preview else "")
                )

        if recommendations:
            lines.append("Top generated recommendations:")
            for rec, movie in recommendations:
                reason_preview = (rec.reason or "").strip()
                if len(reason_preview) > 120:
                    reason_preview = reason_preview[:117] + "..."
                lines.append(
                    f"- {movie.title} | score={rec.score:.3f}"
                    + (f" | reason={reason_preview}" if reason_preview else "")
                )

        return "\n".join(lines)
