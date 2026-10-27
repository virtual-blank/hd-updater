from pathlib import Path
import logging
import logging.config
from typing import Any

from core.config import LoggingSettings, get_logging_settings

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"


def logging_config(settings: LoggingSettings | None = None) -> dict[str, Any]:
    if settings is None:
        settings = get_logging_settings()

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": settings.format
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(LOG_FILE),
                "encoding": "utf-8",
                "maxBytes": 1_000_000,
                "backupCount": 3,
                "formatter": "default",
            }
        },
        "loggers": {
            "httpx": {"level": "WARNING"},
            "httpcore": {"level": "WARNING"},
            "hpack": {"level": "WARNING"},
            "asyncio": {"level": "WARNING"},
            "sqlalchemy.engine": {"level": "WARNING"},
            "aiogram": {"level": "INFO"}, 
            "apscheduler": {"level": "WARNING"},
        },
        "root": {
            "level": settings.level, 
            "handlers": ["console", "file"]
        },
    }


def setup_logging(settings: LoggingSettings | None = None) -> None:
    logging.config.dictConfig(logging_config(settings))