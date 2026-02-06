# backend/app/core/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from typing import Callable
from app.utils.logger import get_logger

logger = get_logger("middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Simple request logging middleware that attaches a request_id and logs
    method/path and timing. Add more context into request.state as needed.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-Id") or f"rid-{request.headers.get('X-Forwarded-For', 'local')}"
        # attach to state for downstream handlers
        request.state.request_id = request_id

        logger.info(f"[{request_id}] --> {request.method} {request.url.path}")
        start = request.scope.get("start_time") or request.scope.setdefault("start_time", 0)
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(f"[{request_id}] Exception while handling request: {exc}")
            raise
        finally:
            pass

        logger.info(f"[{request_id}] <-- {request.method} {request.url.path} {response.status_code}")
        return response
