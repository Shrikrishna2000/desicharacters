# backend/app/routers/session_router.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

from app.services.session_service import (
    create_session,
    get_session,
    update_session_history,
    delete_session,
)
from app.core.security import validate_api_key

router = APIRouter(prefix="/session", tags=["Session"])


# --------------------------
# Pydantic Models
# --------------------------

class Message(BaseModel):
    role: str
    parts: str


class SessionCreateRequest(BaseModel):
    session_id: str
    character: Dict
    history: Optional[List[Message]] = []


class SessionUpdateRequest(BaseModel):
    history: List[Message]


# --------------------------
# Routes
# --------------------------

@router.post("/create")
async def create_session_route(data: SessionCreateRequest):
    """
    Create a new conversation session.
    Stores:
    - character object
    - chat history
    """

    created = await create_session(
        session_id=data.session_id,
        character=data.character,
        history=[msg.dict() for msg in data.history],
    )
    return {"created": created}


@router.get("/{session_id}")
async def get_session_route(session_id: str):
    """Fetch saved session state from Redis."""
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.post("/{session_id}/update")
async def update_session_route(session_id: str, data: SessionUpdateRequest):
    """Append new messages to history."""

    updated = await update_session_history(
        session_id=session_id,
        new_messages=[msg.dict() for msg in data.history],
    )
    return {"updated": updated}


@router.delete("/{session_id}")
async def delete_session_route(session_id: str):
    """Delete stored session completely."""

    deleted = await delete_session(session_id)
    return {"deleted": deleted}
