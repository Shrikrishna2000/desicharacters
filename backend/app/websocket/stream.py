# backend/app/websocket/stream.py
import json
import asyncio
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from starlette.websockets import WebSocketState

from app.utils.logger import get_logger
from app.services.session_service import get_session, create_session, update_session_history
from app.services.chat_service import stream_reply
from app.core.rate_limiter import enforce_rate_limit
from app.utils.helpers import now_ts, generate_uuid
from app.utils.safety import sanitize_user_input, detect_jailbreak_attempt
from app.config.settings import get_settings

logger = get_logger("ws")
router = APIRouter()

settings = get_settings()

HEARTBEAT_INTERVAL = 20  # seconds


@router.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint that supports:
    - resume (client should create session beforehand)
    - user_message streaming
    - heartbeat ping/pong
    """

    await websocket.accept()
    client_id = websocket.headers.get("x-client-id") or generate_uuid("client")
    tab_id = websocket.headers.get("x-tab-id") or generate_uuid("tab")
    logger.info("WS connected: session=%s client=%s tab=%s", session_id, client_id, tab_id)

    # Track last activity for heartbeat
    last_activity = now_ts()
    ping_task = None

    async def heartbeat():
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                try:
                    await websocket.send_text(json.dumps({"type": "ping", "ts": now_ts()}))
                except Exception:
                    break
        except asyncio.CancelledError:
            return

    try:
        # Ensure session exists or create a stub
        session = await get_session(session_id)
        if not session:
            # Create a minimal session placeholder — ensure client will call /session/create in parallel
            # For now, we create a session with empty character to avoid 404 later
            await create_session(session_id=session_id, character={"id": "unknown"}, history=[])
            session = await get_session(session_id)

        # start heartbeat
        ping_task = asyncio.create_task(heartbeat())

        while True:
            raw = await websocket.receive_text()
            last_activity = now_ts()

            # parse
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"type": "user_message", "content": raw}

            ptype = payload.get("type", "user_message")

            # Heartbeat ping/pong handling
            if ptype == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "ts": now_ts()}))
                continue

            if ptype == "resume":
                # Client wants to resume — send last N messages + summary
                session = await get_session(session_id)
                if not session:
                    await websocket.send_text(json.dumps({"type": "error", "message": "session not found"}))
                    continue
                # Send ack + restore
                await websocket.send_text(json.dumps({"type": "ack", "session_id": session_id}))
                await websocket.send_text(json.dumps({"type": "restore", "payload": {"history": session.get("history", [])[-20:], "summary": session.get("summary")}}))
                continue

            if ptype == "user_message":
                # rate limit per client
                try:
                    enforce_rate_limit(client_id, max_requests=30, window=60)
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
                    # send an event indicating streaming start
                    await websocket.send_text(json.dumps({"type": "assistant_stream_start"}))
                    logger.info("Streaming reply started for session=%s", session_id)
                    async for chunk in stream_reply(session_id=session_id, user_message=sanitized):
                        await websocket.send_text(json.dumps({"type": "assistant_stream_chunk", "chunk": chunk}))
                    # send final end event
                    await websocket.send_text(json.dumps({"type": "assistant_stream_end"}))
                    logger.info("Streaming reply ended for session=%s", session_id)

                except Exception as e:
                    logger.exception("Stream failed: %s", e)
                    
                    await websocket.send_text(json.dumps({"type": "error", "message": "AI failed to generate a response."}))
                    continue

                continue

            # unknown message
            await websocket.send_text(json.dumps({"type": "error", "message": f"Unknown message type: {ptype}"}))

    except WebSocketDisconnect:
        logger.info("Websocket disconnected: session=%s client=%s", session_id, client_id)
    except Exception as e:
        logger.exception("Websocket error: %s", e)
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        if ping_task:
            ping_task.cancel()
