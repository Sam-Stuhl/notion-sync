import logging
import logging.handlers
import pathlib

from src.config import settings

LOG_DIR = pathlib.Path("logs")
LOG_FILE = LOG_DIR / "notion-sync.log"


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)-20s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Suppress noisy library loggers
    for noisy in ("notion_client", "httpx", "httpcore", "uvicorn", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
