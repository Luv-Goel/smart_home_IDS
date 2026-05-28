"""Smart Home IDS Backend Package.

This package provides the main FastAPI application and all backend services.
"""

__version__ = "0.1.0"

from backend.main import create_app, get_settings

__all__ = ["create_app", "get_settings"]