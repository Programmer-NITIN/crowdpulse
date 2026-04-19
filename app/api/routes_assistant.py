"""
api/routes_assistant.py
-----------------------
Chatbot endpoint for the Event Assistant.
"""

from fastapi import APIRouter, Depends

from app.ai_engine.chatbot import get_chat_response
from app.middleware.rate_limiter import chat_rate_limit
from app.models.chat_models import ChatRequest, ChatResponse

router = APIRouter()


@router.post(
    "/assistant/chat",
    response_model=ChatResponse,
    summary="Ask the Event Assistant a question",
    dependencies=[Depends(chat_rate_limit)],
)
async def chat(req: ChatRequest):
    """Sends a question to the grounded AI Event Assistant.

    The chatbot classifies intent deterministically, then uses Gemini
    to phrase a response grounded in structured venue data.
    """
    history_dicts = (
        [{"role": h.role, "content": h.content} for h in req.history]
        if req.history
        else None
    )
    reply, intent, grounded = get_chat_response(req.message, history_dicts)
    return ChatResponse(reply=reply, intent=intent, grounded=grounded)
