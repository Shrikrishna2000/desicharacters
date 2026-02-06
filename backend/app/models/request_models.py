# backend/app/models/request_models.py
from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.chat_models import Message


class CreateSessionRequest(BaseModel):
    session_id: str
    character: dict
    history: Optional[List[Message]] = []


class UpdateHistoryRequest(BaseModel):
    new_messages: List[Message]


class ChatSendRequest(BaseModel):
    session_id: str
    user_message: str
