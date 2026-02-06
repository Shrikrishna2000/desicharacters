# backend/app/utils/helpers.py
from typing import Optional
import uuid
import time
import html
import re


def generate_uuid(prefix: Optional[str] = None) -> str:
    uid = str(uuid.uuid4())
    return f"{prefix}-{uid}" if prefix else uid


def now_ts() -> int:
    return int(time.time())


def safe_truncate(text: str, max_chars: int) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def normalize_and_escape(text: str) -> str:
    """
    Lightweight normalization + HTML escape for safe display and prompt usage.
    """
    if not text:
        return ""
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Escape HTML to avoid injection when rendering in clients
    return html.escape(text)
