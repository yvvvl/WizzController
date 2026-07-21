from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config.paths import logs_dir


def configure_logging() -> None:
    """Configura consola + log rotativo sin duplicar handlers."""

    root = logging.getLogger()
    if getattr(root, "_wizz_configured", False):
        return

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    handlers: list[logging.Handler] = []

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    handlers.append(stream)

    try:
        file_handler = RotatingFileHandler(
            logs_dir() / "wizz.log",
            maxBytes=1_500_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except Exception:
        pass

    root.setLevel(logging.INFO)
    for handler in handlers:
        root.addHandler(handler)
    setattr(root, "_wizz_configured", True)
