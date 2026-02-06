# backend/app/core/security.py

import re
import time
import jwt
import html
import unicodedata
from typing import Optional, Dict
from passlib.context import CryptContext
from fastapi import HTTPException, Header

from app.config.settings import get_settings

settings = get_settings()

# -----------------------------
# Password Hashing (for later)
# -----------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


# -----------------------------
# JWT Utilities
# -----------------------------
def create_jwt_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    payload = data.copy()

    expire_time = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    payload["exp"] = int(time.time()) + expire_time * 60

    try:
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return token
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JWT encode failed: {e}")


def decode_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


# -----------------------------
# API Key Validation
# -----------------------------
def validate_api_key(x_api_key: str = Header(None)):
    """Protect any route with X-API-KEY header."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key.")

    if x_api_key != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key.")

    return True


# -----------------------------
# Input Sanitization
# -----------------------------
def sanitize_text(text: str) -> str:
    """
    Prevent prompt injection attempts + unsafe markup.
    """

    if not text:
        return ""

    # 1. Normalize Unicode (removes sneaky homoglyph attacks)
    text = unicodedata.normalize("NFKC", text)

    # 2. Escape HTML tags (<script>, <img onerror>, etc.)
    text = html.escape(text)

    # 3. Remove null bytes and control characters
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)

    # 4. Remove jailbreak keywords pattern-based
    dangerous_patterns = [
        r"ignore( all)? previous instructions",
        r"bypass( system| guardrails| restrictions)",
        r"you are now (free|unrestricted|no longer an ai)",
        r"system override",
    ]

    for p in dangerous_patterns:
        text = re.sub(p, "[filtered]", text, flags=re.IGNORECASE)

    return text


# -----------------------------
# Safe Message Check
# -----------------------------
def ensure_safe_message(content: str):
    """Reject messages that violate safety rules early."""
    forbidden = [
        "system override",
        "ignore previous",
        "disable safety",
        "sudo",
        "root access",
        "run shell",
        "execute code",
        "token leak",
    ]

    for f in forbidden:
        if f.lower() in content.lower():
            raise HTTPException(status_code=400, detail="Unsafe message detected.")

    return True


# -----------------------------
# Optional Rate Limit Helper
# -----------------------------
# (Used by routers with Redis)
def enforce_rate_limit(client_id: str, redis_client, max_requests: int = 30, window_sec: int = 60):
    """
    Sliding window rate limit.
    Use inside any API or Socket handler.
    """

    key = f"ratelimit:{client_id}"
    pipe = redis_client.client.pipeline()

    try:
        now = int(time.time())
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, 0, now - window_sec)
        pipe.zcard(key)
        pipe.expire(key, window_sec)
        _, _, req_count, _ = pipe.execute()

        if req_count > max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Slow down."
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rate limit error: {e}")
