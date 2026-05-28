"""Smart Home IDS Core Package.

This package provides core utilities, base classes, and shared functionality
for all IDS services.
"""

__version__ = "0.1.0"

from ids_core.config import Settings
from ids_core.logger import get_logger, setup_logging

__all__ = ["Settings", "get_logger", "setup_logging"]