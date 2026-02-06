# backend/app/services/session_service.py

import json
from typing import Dict, List, Optional
from fastapi import HTTPException
from app.utils.logger import get_logger
from app.storage.redis_client import redis_client

logger = get_logger("session_service")

MAX_HISTORY_LENGTH = 120
# --------------------------
# Helpers for Redis Keys
# --------------------------

def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


# --------------------------
# Create Session
# --------------------------

async def create_session(session_id: str, character: Dict, history: List[Dict]):
    """Create new session with character + chat history."""
    logger.info("Creating session: %s", session_id)

    try:
        key = _session_key(session_id)

        session_payload = {
            "character": character,
            "history": history,
        }

        await redis_client.set(key, json.dumps(session_payload), ex=60*60)  # 24h expiry
        return True

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e}")


# --------------------------
# Get Session
# --------------------------

async def get_session(session_id: str) -> Optional[Dict]:
    try:
        raw = await redis_client.get(_session_key(session_id))
        if not raw:
            return None
        return json.loads(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {e}")


async def update_session_history(session_id: str, new_messages: List[Dict]):
    try:
        key = _session_key(session_id)

        logger.info("Updating session: %s with %d new messages", session_id, len(new_messages))
        # ------------------------------
        # 1) Fetch raw from Redis
        # ------------------------------

        raw = await redis_client.get(key)

        if raw is None:
            raise HTTPException(status_code=404, detail="Session not found")

        # redis_client.get() may return BYTES → decode safely
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        # ------------------------------
        # 2) Parse JSON safely
        # ------------------------------
        try:
            session = json.loads(raw)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Corrupted session data in Redis"
            )

        # Ensure "history" exists
        if "history" not in session:
            session["history"] = []

        # ------------------------------
        # 3) Append new messages
        # ------------------------------
        if not isinstance(new_messages, list):
            raise HTTPException(status_code=400, detail="new_messages must be a list")

        session["history"].extend(new_messages)

        # Trim LRU
        session["history"] = session["history"][-MAX_HISTORY_LENGTH:]

        # ------------------------------
        # 4) Save back to Redis
        # ------------------------------
        await redis_client.set(key, json.dumps(session), ex=86400)

        return True

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update session %s: %s", session_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update session: {str(e)}"
        )

# --------------------------
# Delete Session
# --------------------------
async def delete_session(session_id: str) -> bool:
    try:
        key = _session_key(session_id)
        redis_client.delete(key)
        logger.info("Deleting session: %s", session_id)
        return True
    except Exception as e:
        logger.exception("Failed to Delete session %s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {e}")
