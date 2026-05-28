"""Logger setup and utilities for Smart Home IDS.

This module provides JSON-formatted logging using structlog for
consistent log formatting across all services.
"""

import logging
import sys
import os
from typing import Any

import structlog
from structlog.types import EventDict

from ids_core.config import settings, LogConfig


def _drop_color_mapping(event: EventDict) -> EventDict:
    """Drop color mapping from event dict for production logs."""
    return {key: value for key, value in event.items() if key != "color"}


def setup_logging() -> None:
    """Configure structlog and logging for the application."""
    log_config = LogConfig()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.Stack_infoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure handler based on output
    if log_config.output == "stdout":
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(log_config.output)

    # Create formatter based on format setting
    if log_config.format == "json":
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_logger_name,
            ],
        )
    else:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=not log_config.output.startswith("/")),
            foreign_pre_chain=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_logger_name,
            ],
        )

    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_config.level))
    root_logger.addHandler(handler)

    # Also configure structlog's logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.Stack_infoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        processors=[
            structlog.contextvars.merge_contextvars,
            _drop_color_mapping,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.Stack_infoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Optional logger name. If None, uses module name.

    Returns:
        A BoundLogger instance with context.
    """
    return structlog.get_logger(name)


# Convenience functions for common log operations
def log_info(message: str, **kwargs: Any) -> None:
    """Log an info message."""
    logger = get_logger()
    logger.info(message, **kwargs)


def log_error(message: str, **kwargs: Any) -> None:
    """Log an error message."""
    logger = get_logger()
    logger.error(message, **kwargs)


def log_warning(message: str, **kwargs: Any) -> None:
    """Log a warning message."""
    logger = get_logger()
    logger.warning(message, **kwargs)


def log_debug(message: str, **kwargs: Any) -> None:
    """Log a debug message."""
    logger = get_logger()
    logger.debug(message, **kwargs)


def log_critical(message: str, **kwargs: Any) -> None:
    """Log a critical message."""
    logger = get_logger()
    logger.critical(message, **kwargs)