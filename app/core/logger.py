import logging
import os
from typing import Optional


_LOGGING_CONFIGURED = False


def setup_logging(default_level: str = "INFO") -> None:
    """Configure root logging once for the application process."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", default_level).upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    _LOGGING_CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger by name after ensuring logging is configured."""
    setup_logging()
    return logging.getLogger(name or "skillbridge")
