"""Smart Home IDS Schemas Package.

This package provides Pydantic models and schemas for event data,
API requests/responses, and cross-service communication.
"""

__version__ = "0.1.0"

from ids_schemas.base import IDSBasemodel
from ids_schemas.alert import AlertEvent, AlertPayload, AlertSeverity
from ids_schemas.device import DeviceEvent, DeviceState
from ids_schemas.flow import FlowEvent, FlowRecord, FlowFeature
from ids_schemas.health import HealthEvent, HealthStatus
from ids_schemas.inference import InferenceEvent, InferenceResult
from ids_schemas.auth import AuthToken, UserCredentials, UserRole

__all__ = [
    "IDSBasemodel",
    "AlertEvent",
    "AlertPayload",
    "AlertSeverity",
    "DeviceEvent",
    "DeviceState",
    "FlowEvent",
    "FlowRecord",
    "FlowFeature",
    "HealthEvent",
    "HealthStatus",
    "InferenceEvent",
    "InferenceResult",
    "AuthToken",
    "UserCredentials",
    "UserRole",
]