"""Chat schemas"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat request from clients"""

    message: str = Field(..., min_length=1, max_length=8000)
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)


class ChatResponse(BaseModel):
    """Normalized chat response returned to clients"""

    reply: str
    model: str
