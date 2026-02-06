# backend/app/utils/logger.py
import logging
from logging.handlers import RotatingFileHandler
from app.config.settings import get_settings

settings = get_settings()

LOG_FILE = "logs/app.log"


def get_logger(name: str = "desicharacters"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logger.setLevel(level)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter("%(asctime)s — %(levelname)s — %(name)s — %(message)s"))

    # Rotating file handler
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter("%(asctime)s — %(levelname)s — %(name)s — %(message)s"))

    logger.addHandler(ch)
    logger.addHandler(fh)

    # avoid duplicate logs
    logger.propagate = False
    return logger
