"""Routers module for Smart Home IDS.

This module provides all API routers.
"""

from backend.routers import alerts, devices, auth, health

__all__ = ["alerts", "devices", "auth", "health"]