"""
Simple logging configuration for SimEcon project.

Usage:
    from logging_config import get_logger

    logger = get_logger(__name__)
    logger.debug("Debug message")
    logger.info("Info message")
"""

import logging
import os
import sys


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name."""
    return logging.getLogger(name)


def setup_logging(level: str = "DEBUG"):
    """Setup basic logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.DEBUG),
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    # Silence noisy third-party loggers
    logging.getLogger("matplotlib").setLevel(logging.WARNING)


# Auto-setup based on environment
if "pytest" in sys.modules:
    setup_logging("WARNING")  # Quiet during tests
else:
    level = os.getenv("LOG_LEVEL", "DEBUG")
    setup_logging(level)
