# backend/app/core/rate_limiter.py
import time
from fastapi import HTTPException
from app.storage.redis_client import redis_client
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger("rate_limiter")

settings = get_settings()

# Default limits
DEFAULT_MAX_REQUESTS = 60
DEFAULT_WINDOW = 60  # seconds


def _rate_limit_key(client_id: str) -> str:
    return f"ratelimit:{client_id}"


async def is_rate_limited(client_id: str, max_requests: int = DEFAULT_MAX_REQUESTS, window: int = DEFAULT_WINDOW) -> bool:
    """
    Sliding window rate limiter using a Redis sorted set.
    Returns True if the client is rate limited.
    """
    now = int(time.time())
    key = _rate_limit_key(client_id)

    try:
        pipe = redis_client.client.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
        pipe.expire(key, window + 5)
        _, _, count, _ = await pipe.execute()  # ✅ await it now
        return int(count) > max_requests
    except Exception:
        logger.info("Client %s hit rate limit", client_id)
        logger.debug("Current request count=%d for client %s", count, client_id)
        # On error, fail-open (do not block)
        return False


async def enforce_rate_limit(client_id: str, max_requests: int = DEFAULT_MAX_REQUESTS, window: int = DEFAULT_WINDOW):
    if await is_rate_limited(client_id, max_requests=max_requests, window=window):
        raise HTTPException(status_code=429, detail="Too many requests. Slow down.")
