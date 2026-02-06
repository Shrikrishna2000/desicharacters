# backend/app/services/chat_service.py
import asyncio
import json
from typing import AsyncGenerator, List, Dict, Optional
from fastapi import HTTPException
from app.services.summarization_service import summarize_conversation

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config.settings import get_settings
from app.services.session_service import get_session, update_session_history
from app.utils.prompt_builder import build_character_prompt
from app.utils.safety import sanitize_user_input, detect_jailbreak_attempt, quick_moderation_check
from app.services.summarization_service import summarize_messages
from app.utils.helpers import safe_truncate
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger("chat_service")

# Initialize LLM client (used for both chat & summarization).
# Note: for streaming, we check for a `stream` method; if none exists we fallback to chunking the final reply.
LLM = ChatGoogleGenerativeAI(
    model=getattr(settings, "GOOGLE_MODEL", None),
    temperature=0.7,
    google_api_key=getattr(settings, "GOOGLE_API_KEY", None),
)


async def _call_llm_sync(messages: List, timeout: int = 60) -> str:
    """
    Call the LLM synchronously in a thread to avoid blocking the event loop.
    Returns the final text content.
    """
    loop = asyncio.get_running_loop()

    def invoke():
        try:
            resp = LLM.invoke(messages)
            return resp.content
        except Exception as e:
            # bubble up
            raise e

    try:
        return await loop.run_in_executor(None, invoke)
    except Exception as e:
        logger.exception("LLM invoke failed: %s", e)
        raise HTTPException(status_code=500, detail=f"LLM invoke failed: {e}")


async def generate_reply(session_id: str, user_message: str) -> str:
    """
    Non-streaming reply. Validates input, constructs the prompt & context,
    calls LLM synchronously (in thread), stores history, and returns text.
    """
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    character = session.get("character", {})
    history = session.get("history", []) or []

    # Safety & sanitization
    sanitized = sanitize_user_input(user_message)
    if not quick_moderation_check(sanitized):
        logger.warning("User message rejected by moderation: %s", sanitized)
        raise HTTPException(status_code=400, detail="Message rejected by moderation.")

    if detect_jailbreak_attempt(sanitized):
        logger.warning("Jailbreak attempt detected in session %s: %s", session_id, sanitized)
        reply = "I can't follow that request. Let's keep the conversation safe and in-character."
        await update_session_history(session_id, [{"role": "user", "parts": sanitized}, {"role": "assistant", "parts": reply}])
        return reply

    # Build prompt
    system_prompt = build_character_prompt(character)

    # Prepare messages: system + summary (if present) + last N messages
    messages_for_llm = [SystemMessage(content=system_prompt)]

    # If there's a summary, include it (session may store summary later)
    if session.get("summary"):
        messages_for_llm.append(SystemMessage(content=f"[Memory Summary]: {safe_truncate(session.get('summary'), 2000)}"))

    # Include last 10 messages
    last_msgs = history[-10:] if history else []
    for m in last_msgs:
        if m["role"] == "user":
            messages_for_llm.append(HumanMessage(content=m["parts"]))
        elif m["role"] == "assistant":
            messages_for_llm.append(AIMessage(content=m["parts"]))

    # Append the new user message
    messages_for_llm.append(HumanMessage(content=sanitized))

    # Call LLM (sync-in-thread)
    logger.info("Generating reply for session=%s message=%s", session_id, sanitized)
    reply_text = await _call_llm_sync(messages_for_llm)

    # Store messages
    await update_session_history(session_id, [{"role": "user", "parts": sanitized}, {"role": "assistant", "parts": reply_text}])

    # Optionally trigger summarization in background if history large
    if len(history) + 2 > 15:
        # fire and forget summarization (session service will store summary)
        asyncio.create_task(_maybe_summarize_session(session_id))

    return reply_text


async def _maybe_summarize_session(session_id: str):
    """
    Load session, check if summarization needed, call summarizer and save summary to session.
    This runs in background so user flow is not blocked.
    """
    try:
        session = await get_session(session_id)
        if not session:
            return
        history = session.get("history", []) or []
        # if already short, skip
        if len(history) < 30:
            return

        # Compose summarization input from older messages (all except last 20)
        older = history[:-20]
        if not older:
            return

        summary_text = await summarize_messages(older, max_sentences=2)
        # store summary: we will use session_service.update_session_summary (not implemented yet)
        # For now, reuse update_session_history to save a system summary message
        await update_session_history(session_id, [{"role": "system", "parts": f"[SUMMARY]: {summary_text}"}])
        logger.info("Session %s summarized and stored.", session_id)
    except Exception as e:
        logger.exception("Background summarization failed for session %s: %s", session_id, e)


# --------------------------
# Streaming helpers
# --------------------------

def _chunk_text(text: str, chunk_size: int = 64):
    """Yield text chunks of approx chunk_size characters (simple splitter)."""
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        yield text[start:end]
        start = end


async def stream_reply(session_id: str, user_message: str) -> AsyncGenerator[str, None]:
    """
    Provide an async generator that yields chat tokens/chunks for streaming over WS.
    If the LLM client has streaming support, hook it in; otherwise we fallback to
    synchronous invoke and chunk the final reply.
    """
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # sanitize & check
    sanitized = sanitize_user_input(user_message)
    if detect_jailbreak_attempt(sanitized):
        yield "I can't follow that request. Let's keep the conversation safe and in-character."
        return

    # Build messages as in generate_reply
    character = session.get("character", {})
    history = session.get("history", []) or []
    system_prompt = build_character_prompt(character)

    messages_for_llm = [SystemMessage(content=system_prompt)]
    if session.get("summary"):
        messages_for_llm.append(SystemMessage(content=f"[Memory Summary]: {safe_truncate(session.get('summary'), 2000)}"))
    for m in history[-10:]:
        if m["role"] == "user":
            messages_for_llm.append(HumanMessage(content=m["parts"]))
        elif m["role"] == "assistant":
            messages_for_llm.append(AIMessage(content=m["parts"]))
    messages_for_llm.append(HumanMessage(content=sanitized))

    # If LLM exposes a stream API, use it. Otherwise fallback to a chunked invoke.
    if hasattr(LLM, "stream"):
        # The actual streaming interface depends on the library; here's a generic pattern.
        loop = asyncio.get_running_loop()

        def blocking_stream_call():
            # This expects LLM.stream to yield partial responses synchronously;
            # adapt to your LLM client's actual streaming API.
            for chunk in LLM.stream(messages_for_llm):
                yield chunk

        # Run the blocking iterator in a thread and yield chunks asynchronously
        try:
            logger.debug("Streaming reply to session=%s", session_id)

            for chunk in await loop.run_in_executor(None, lambda: list(LLM.stream(messages_for_llm))):
                # chunk may be dict or string; convert accordingly
                text_chunk = chunk if isinstance(chunk, str) else getattr(chunk, "content", str(chunk))
                yield text_chunk
        except Exception as e:
            
            logger.exception("Streaming LLM failed, falling back to batch invoke: %s", e)
            # fallback below
    # fallback: non-streaming
    final = await _call_llm_sync(messages_for_llm)
    # append to session history at the end of the stream
    for piece in _chunk_text(final, chunk_size=80):
        yield piece

    # Finally, persist both user + assistant
    await update_session_history(session_id, [{"role": "user", "parts": sanitized}, {"role": "assistant", "parts": final}])


def format_history(history: List[Dict[str, str]]) -> List:
    """
    Convert raw dict messages into LangChain Human/AI/SystemMessage objects.
    """
    formatted = []
    for msg in history:
        role = msg.get("role")
        content = msg.get("parts") or msg.get("content", "")

        if role == "user":
            formatted.append(HumanMessage(content=content))
        elif role == "assistant":
            formatted.append(AIMessage(content=content))
        elif role == "system":
            formatted.append(SystemMessage(content=content))

    return formatted

async def generate_summary(history: List[Dict[str, str]]) -> str:
    """
    High-level summary generator wrapper.
    Called by chat_router or session_router.
    """
    text = "\n".join([f"{m['role']}: {m['parts']}" for m in history])
    return await summarize_conversation(text)