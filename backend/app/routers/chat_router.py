# backend/app/routers/chat_router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from fastapi import WebSocket, WebSocketDisconnect
from app.services.chat_service import (
    generate_reply,
    generate_summary,
)
from app.core.rate_limiter import enforce_rate_limit


router = APIRouter(prefix="/chat", tags=["Chat"])


# --------------------------
# Pydantic Models
# --------------------------

class Message(BaseModel):
    role: str
    parts: str

class ChatRequest(BaseModel):
    session_id: str
    user_message: str

class SummaryRequest(BaseModel):
    history: List[Message]


# --------------------------
# Routes
# --------------------------

@router.post("/send")
async def chat_send(data: ChatRequest):
    """
    Generate an AI reply using:
    - Stored character object
    - Stored chat history
    """
    # Rate limit per session or per user
    enforce_rate_limit(data.session_id)  # or user.id if you have auth
    
    try:
        response = await generate_reply(
            session_id=data.session_id,
            user_message=data.user_message
        )
        return {"reply": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summary")
async def chat_summary(data: SummaryRequest):
    """
    Create a short abstractive summary of the conversation.
    """
    enforce_rate_limit("summary")  
    try:
        summary = await generate_summary(
            [m.dict() for m in data.history]
        )
        return {"summary": summary}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
