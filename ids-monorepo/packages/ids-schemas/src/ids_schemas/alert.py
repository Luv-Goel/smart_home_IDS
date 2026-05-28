"""Alert schemas for Smart Home IDS.

This module provides Pydantic models for alert events and related data.
"""

from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ids_schemas.base import IDSBasemodel


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertCategory(str, Enum):
    """Alert category types."""

    NETWORK_ANOMALY = "NETWORK_ANOMALY"
    DDOS_ATTEMPT = "DDoS_ATTEMPT"
    PORT_SCAN = "PORT_SCAN"
    ARP_SPOOFING = "ARP_SPOOFING"
    MALWARE_COMMUNICATION = "MALWARE_COMMUNICATION"
    BRUTE_FORCE = "BRUTE_FORCE"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    SUSPICIOUS_TRAFFIC = "SUSPICIOUS_TRAFFIC"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    SYSTEM_ANOMALY = "SYSTEM_ANOMALY"


class AlertPayload(BaseModel):
    """Detailed alert payload with context."""

    alert_type: str = Field(description="Type of alert")
    category: AlertCategory = Field(description="Alert category")
    severity: AlertSeverity = Field(description="Severity level")
    confidence_score: float = Field(ge=0.0, le=1.0, description="ML confidence score")
    description: str = Field(description="Human-readable alert description")
    source_ip: str | None = Field(default=None, description="Source IP address")
    destination_ip: str | None = Field(default=None, description="Destination IP address")
    source_mac: str | None = Field(default=None, description="Source MAC address")
    destination_mac: str | None = Field(default=None, description="Destination MAC address")
    source_port: int | None = Field(default=None, ge=0, le=65535, description="Source port")
    destination_port: int | None = Field(default=None, ge=0, le=65535, description="Destination port")
    protocol: str | None = Field(default=None, description="Network protocol")
    timestamp: str = Field(description="Timestamp of the alert")
    feature_vector: dict[str, Any] | None = Field(default=None, description="Feature vector used for detection")
    ml_metadata: dict[str, Any] | None = Field(default=None, description="ML inference metadata")
    additional_data: dict[str, Any] = Field(default_factory=dict, description="Additional alert data")


class AlertEvent(IDSBasemodel):
    """Complete alert event for MQTT publishing."""

    event_type: Literal["alert"] = "alert"
    node_id: str = Field(description="Edge node identifier")
    device_id: str = Field(description="Device identifier (MAC address)")
    device_ip: str | None = Field(default=None, description="Device IP address")
    payload: AlertPayload = Field(description="Alert payload")
    is_false_positive: bool = Field(default=False, description="Whether alert is confirmed false positive")
    is_resolved: bool = Field(default=False, description="Whether alert has been resolved")


class AlertQueryParams(BaseModel):
    """Query parameters for alert filtering."""

    start_time: str | None = Field(default=None, description="Start time filter (ISO format)")
    end_time: str | None = Field(default=None, description="End time filter (ISO format)")
    severity: list[AlertSeverity] | None = Field(default=None, description="Severity filter")
    category: list[AlertCategory] | None = Field(default=None, description="Category filter")
    device_id: str | None = Field(default=None, description="Device MAC filter")
    node_id: str | None = Field(default=None, description="Edge node filter")
    is_resolved: bool | None = Field(default=None, description="Resolved status filter")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=1000, description="Records per page")