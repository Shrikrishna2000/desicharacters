# backend/app/models/chat_models.py
from pydantic import BaseModel, Field
from typing import Literal, List
from datetime import datetime


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    parts: str = Field(..., max_length=5000)
    ts: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))


class ChatSummary(BaseModel):
    version: str = "v1"
    summary: str
    created_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))


class CharacterMeta(BaseModel):
    id: str
    name: str
    version: str
    visual_short: str | None = None
    personality_short: str | None = None
    tags: List[str] = []
