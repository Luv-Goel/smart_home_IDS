"""Database module for Smart Home IDS.

This module provides database configuration, session management,
and model imports.
"""

__version__ = "0.1.0"

from backend.database.config import DatabaseConfig, get_database_config
from backend.database.session import get_async_session, AsyncSessionLocal
from backend.database.models import (
    Device,
    FlowRecord,
    Alert,
    Anomaly,
    User,
    Threshold,
    ModelMetadata,
    AuditLog,
)

__all__ = [
    "DatabaseConfig",
    "get_database_config",
    "get_async_session",
    "AsyncSessionLocal",
    "Device",
    "FlowRecord",
    "Alert",
    "Anomaly",
    "User",
    "Threshold",
    "ModelMetadata",
    "AuditLog",
]