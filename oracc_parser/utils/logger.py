"""
Logging configuration for oracc-parser.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

_LOGGER_NAME = "oracc_parser"
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Return the package-wide logger, creating it on first call."""
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger(_LOGGER_NAME)
    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)

    return _logger
