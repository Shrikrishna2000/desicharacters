# backend/app/services/summarization_service.py
import asyncio
from typing import List
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config.settings import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger("summarization_service")

# Light-weight summarization LLM
SUM_LLM = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.3,
    google_api_key=getattr(settings, "GOOGLE_API_KEY", None)
)


async def summarize_conversation(text: str, max_sentences: int = 3) -> str:
    """
    Summaries a long text conversation into a concise memory block.
    """
    prompt = (
        "Summarize the following conversation into "
        f"{max_sentences} sentences max. Keep only the essential facts.\n\n"
        f"Conversation:\n{text}"
    )

    try:
        loop = asyncio.get_running_loop()
        def call():
            resp = SUM_LLM.invoke([HumanMessage(content=prompt)])
            return resp.content.strip()

        return await loop.run_in_executor(None, call)

    except Exception as e:
        logger.exception("Summarization failed: %s", e)
        return ""


async def summarize_messages(messages: List[dict], max_sentences: int = 3) -> str:
    """
    Summaries a list of message dicts:
    [
        {"role": "user", "parts": "..."},
        {"role": "assistant", "parts": "..."},
        ...
    ]
    """
    text_blocks = []
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("parts") or m.get("content", "")
        text_blocks.append(f"{role}: {content}")

    combined_text = "\n".join(text_blocks)

    return await summarize_conversation(combined_text, max_sentences=max_sentences)
