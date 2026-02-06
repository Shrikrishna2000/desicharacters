# backend/app/routers/websocket_router.py

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from typing import Optional

from app.services.chat_service import stream_reply
from app.services.session_service import get_session, create_session
from app.utils.helpers import now_ts, generate_uuid
from app.utils.safety import sanitize_user_input, detect_jailbreak_attempt
from app.core.rate_limiter import enforce_rate_limit
from app.utils.logger import get_logger

logger = get_logger("websocket")

router = APIRouter(prefix="/ws", tags=["WebSocket"])

HEARTBEAT_INTERVAL = 20  # seconds
IDLE_TIMEOUT = 120       # seconds
RATE_LIMIT = 30
RATE_WINDOW = 60  # seconds


@router.websocket("/chat/{session_id}")
async def ws_chat(session_id: str, websocket: WebSocket):
    """
    Production-ready WebSocket endpoint:
    - Resume / restore session
    - Streaming AI replies
    - Rate limiting per client
    - Heartbeat ping/pong with idle timeout
    """
    await websocket.accept()
    client_id = websocket.headers.get("x-client-id") or generate_uuid("client")
    tab_id = websocket.headers.get("x-tab-id") or generate_uuid("tab")
    logger.info("WS connected: session=%s client=%s tab=%s", session_id, client_id, tab_id)

    last_activity = now_ts()
    heartbeat_task: Optional[asyncio.Task] = None

    # Heartbeat coroutine
    async def heartbeat():
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                # disconnect if idle
                if now_ts() - last_activity > IDLE_TIMEOUT:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Disconnected due to inactivity"}))
                    await websocket.close()
                    break
                await websocket.send_text(json.dumps({"type": "ping", "ts": now_ts()}))
        except asyncio.CancelledError:
            return

    try:
        # Ensure session exists
        session = await get_session(session_id)
        if not session:
            await create_session(session_id=session_id, character={"id": "unknown"}, history=[])
            session = await get_session(session_id)

        # Start heartbeat
        heartbeat_task = asyncio.create_task(heartbeat())

        while True:
            raw = await websocket.receive_text()
            last_activity = now_ts()

            # Parse payload
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"type": "user_message", "content": raw}

            ptype = payload.get("type", "user_message")

            # Ping/pong handling
            if ptype == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "ts": now_ts()}))
                continue

            # Resume / restore
            if ptype == "resume":
                session = await get_session(session_id)
                if not session:
                    await websocket.send_text(json.dumps({"type": "error", "message": "session not found"}))
                    continue
                await websocket.send_text(json.dumps({"type": "ack", "session_id": session_id}))
                await websocket.send_text(
                    json.dumps({
                        "type": "restore",
                        "payload": {
                            "history": session.get("history", [])[-20:],  # last 20 messages
                            "summary": session.get("summary")
                        }
                    })
                )
                continue

            # User message
            if ptype == "user_message":
                # Rate limit
                try:
                    await enforce_rate_limit(client_id, max_requests=RATE_LIMIT, window=RATE_WINDOW)
                except Exception as e:
                    await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
                    continue

                user_text = payload.get("content", "")
                sanitized = sanitize_user_input(user_text)
                if detect_jailbreak_attempt(sanitized):
                    await websocket.send_text(json.dumps({"type": "assistant", "content": "I cannot comply with that request."}))
                    continue

                # Stream reply
                try:
                    await websocket.send_text(json.dumps({"type": "assistant_stream_start"}))
                    async for chunk in stream_reply(session_id=session_id, user_message=sanitized):
                        await websocket.send_text(json.dumps({"type": "assistant_stream_chunk", "chunk": chunk}))
                    await websocket.send_text(json.dumps({"type": "assistant_stream_end"}))
                except Exception as e:
                    logger.exception("Stream failed: %s", e)
                    await websocket.send_text(json.dumps({"type": "error", "message": "AI failed to generate a response."}))
                continue

            # Unknown type
            await websocket.send_text(json.dumps({"type": "error", "message": f"Unknown message type: {ptype}"}))

    except WebSocketDisconnect:
        logger.info("WS disconnected: session=%s client=%s", session_id, client_id)
    except Exception as e:
        logger.exception("WebSocket error: %s", e)
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
