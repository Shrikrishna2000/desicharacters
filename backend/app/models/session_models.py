# backend/app/models/session_models.py
from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.chat_models import Message, CharacterMeta
from datetime import datetime


class SessionMeta(BaseModel):
    session_id: str
    character: CharacterMeta
    created_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    last_updated: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    expires_at: Optional[int] = None


class SessionPayload(BaseModel):
    meta: SessionMeta
    history: List[Message] = []
    summary: Optional[str] = None
