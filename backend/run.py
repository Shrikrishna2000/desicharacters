# backend/run.py
import os
import uvicorn
from app.config.settings import get_settings

settings = get_settings()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    debug = settings.DEBUG

    workers = 1
    if not debug and os.name != "nt":
        workers = 4

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        workers=workers,
    )
