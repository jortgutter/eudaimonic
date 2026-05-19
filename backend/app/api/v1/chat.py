"""Chat endpoints"""
from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/completions", response_model=ChatResponse, summary="Chat Completion")
async def chat_completion(
    chat_in: ChatRequest,
) -> ChatResponse:
    """Proxy chat completion calls to configured Open WebUI server"""
    return await ChatService.create_completion(chat_in)
