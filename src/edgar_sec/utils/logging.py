"""Logging configuration for the EDGAR SEC client."""

import logging
import sys
from pathlib import Path


def setup_logging(log_file: Path | None = None, level: int = logging.INFO) -> None:
    """Set up logging configuration.

    Args:
        log_file: Optional path to log file. If None, logs to stderr only.
        level: Logging level (default: INFO).
    """
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )
