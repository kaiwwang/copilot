import logging
from logging import Logger

from app.core.config import Settings


def get_logger(settings: Settings) -> Logger:
    """
    Configure and return a module-level logger.
    """
    logger = logging.getLogger(settings.app_name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(settings.log_level.upper())
    return logger

