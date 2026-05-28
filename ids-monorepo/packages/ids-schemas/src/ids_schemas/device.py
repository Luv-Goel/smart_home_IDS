"""Device schemas for Smart Home IDS.

This module provides Pydantic models for device events and state tracking.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ids_schemas.base import IDSBasemodel


class DeviceState(str, Enum):
    """Device connection states."""

    DISCOVERED = "DISCOVERED"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    SUSPICIOUS = "SUSPICIOUS"
    BLOCKED = "BLOCKED"
    TRUSTED = "TRUSTED"
    UNKNOWN = "UNKNOWN"


class DeviceType(str, Enum):
    """Device type classifications."""

    SMART_PHONE = "SMART_PHONE"
    TABLET = "TABLET"
    LAPTOP = "LAPTOP"
    DESKTOP = "DESKTOP"
    SMART_TV = "SMART_TV"
    IoT_SENSOR = "IoT_SENSOR"
    IoT_ACTUATOR = "IoT_ACTUATOR"
    CAMCORDER = "CAMCORDER"
    PRINTER = "PRINTER"
    ROUTER = "ROUTER"
    BRIDGE = "BRIDGE"
    GATEWAY = "GATEWAY"
    UNKNOWN = "UNKNOWN"


class DevicePayload(BaseModel):
    """Device information payload."""

    mac_address: str = Field(description="Device MAC address")
    ip_address: str | None = Field(default=None, description="Device IP address")
    hostname: str | None = Field(default=None, description="Device hostname")
    device_type: DeviceType | None = Field(default=None, description="Device type")
    vendor: str | None = Field(default=None, description="Device vendor/manufacturer")
    first_seen: str = Field(description="First seen timestamp")
    last_seen: str = Field(description="Last seen timestamp")
    connection_count: int = Field(default=0, description="Number of connections")
    total_bytes_up: int = Field(default=0, description="Total bytes uploaded")
    total_bytes_down: int = Field(default=0, description="Total bytes downloaded")
    is_trusted: bool = Field(default=False, description="Whether device is trusted")
    is_blocked: bool = Field(default=False, description="Whether device is blocked")
    last_seen_port: int | None = Field(default=None, description="Last seen on port")
    operating_system: str | None = Field(default=None, description="Detected OS")
    user_agent: str | None = Field(default=None, description="HTTP user agent")
    protocols: list[str] = Field(default_factory=list, description="Detected protocols")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Classification confidence")


class DeviceEvent(IDSBasemodel):
    """Complete device event for MQTT publishing."""

    event_type: Literal["device"] = "device"
    node_id: str = Field(description="Edge node identifier")
    state: DeviceState = Field(description="Device state")
    payload: DevicePayload = Field(description="Device payload")
    event_reason: str | None = Field(default=None, description="Reason for the event")
    anomaly_detected: bool = Field(default=False, description="Whether an anomaly was detected")
    anomaly_details: str | None = Field(default=None, description="Details of detected anomaly")


class DeviceQueryParams(BaseModel):
    """Query parameters for device filtering."""

    mac_address: str | None = Field(default=None, description="Filter by MAC address")
    ip_address: str | None = Field(default=None, description="Filter by IP address")
    device_type: list[DeviceType] | None = Field(default=None, description="Filter by device type")
    is_trusted: bool | None = Field(default=None, description="Filter by trust status")
    is_blocked: bool | None = Field(default=None, description="Filter by block status")
    state: list[DeviceState] | None = Field(default=None, description="Filter by state")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=1000, description="Records per page")