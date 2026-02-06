# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.core.middleware import RequestLoggingMiddleware

# Routers
from app.routers.chat_router import router as chat_router
from app.routers.session_router import router as session_router
from app.routers.health_router import router as health_router
from app.routers.character_router import router as character_router
from app.routers.websocket_router import router as websocket_router_1

# WebSocket router
from app.websocket.stream import router as websocket_router

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Jumbo Backend",
        version="1.0.0",
        description="AI chat backend with sessions, characters, and streaming WebSockets."
    )

    # ---------------------------
    # CORS
    # ---------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------
    # Custom Middlewares
    # ---------------------------
    app.add_middleware(RequestLoggingMiddleware)

    # ---------------------------
    # Include Routers (HTTP)
    # ---------------------------
    app.include_router(health_router)
    app.include_router(session_router)
    app.include_router(chat_router)
    app.include_router(character_router)
    app.include_router(websocket_router_1)

    # ---------------------------
    # Include WebSocket Router
    # ---------------------------
    app.include_router(websocket_router)

    return app


app = create_app()