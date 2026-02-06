# backend/app/utils/safety.py
import re
import unicodedata
from fastapi import HTTPException
from app.config.settings import get_settings
from app.utils.helpers import normalize_and_escape, safe_truncate

settings = get_settings()

# Simple blacklist - replace with moderation API in prod
SIMPLE_BLACKLIST = [
    "nsfw",
    "porn",
    "suicide",
    "bomb",
    "kill",
    "genocide",
    "hate",
    "terror",
    
]


def sanitize_user_input(text: str) -> str:
    """
    Normalize, strip control characters, remove zero-width chars, escape HTML,
    and truncate to a reasonable limit.
    """
    if not text:
        return ""

    # Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # Remove zero-width and control
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)

    # Collapse whitespace
    text = " ".join(text.split())

    # Escape potentially dangerous markup for safe prompt embedding / display
    text = normalize_and_escape(text)

    # Truncate to a safe maximum for a single user utterance
    text = safe_truncate(text, 3000)
    return text


def detect_jailbreak_attempt(text: str) -> bool:
    """
    Look for common jailbreak patterns. This is a heuristic and should be
    complemented by a moderation API in production.
    """
    if not text:
        return False

    t = text.lower()
    patterns = [
        r"ignore (all )?previous instructions",
        r"disregard (all )?prior instructions",
        r"you are now (free|unrestricted|no longer an ai)",
        r"bypass (safety|filters|guardrails)",
        r"pretend to be a (human|person)",
        r"act as if you are not an ai",
        r"system:\s*",
        r"sudo ",
    ]

    for p in patterns:
        if re.search(p, t):
            return True

    # Blacklist check
    for b in SIMPLE_BLACKLIST:
        if b in t:
            return True

    return False


def quick_moderation_check(text: str) -> bool:
    """
    Return True if content is allowed, False if it should be rejected.
    This is intentionally conservative.
    """
    if not text:
        return True

    t = text.lower()
    # simple forbidden phrases
    for forbidden in ["sexual content", "self harm", "bomb", "kill", "suicide"]:
        if forbidden in t:
            return False

    # simple blacklist words
    for b in SIMPLE_BLACKLIST:
        if b in t:
            return False

    return True
