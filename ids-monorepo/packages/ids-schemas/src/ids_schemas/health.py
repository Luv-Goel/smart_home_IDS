"""Health and system status schemas for Smart Home IDS.

This module provides Pydantic models for system health events and status reports.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from ids_schemas.base import IDSBasemodel


class HealthStatus(str, Enum):
    """System health status."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class ComponentStatus(BaseModel):
    """Status of a specific component."""

    name: str = Field(description="Component name")
    status: HealthStatus = Field(description="Component health status")
    message: str | None = Field(default=None, description="Status message")
    uptime_seconds: float | None = Field(default=None, description="Component uptime")
    last_check: str = Field(description="Last health check timestamp")


class SystemMetrics(BaseModel):
    """System resource metrics."""

    cpu_percent: float = Field(description="CPU usage percentage")
    memory_percent: float = Field(description="Memory usage percentage")
    memory_used_bytes: int = Field(description="Memory used in bytes")
    memory_total_bytes: int = Field(description="Total memory in bytes")
    disk_percent: float = Field(description="Disk usage percentage")
    network_received_bytes: int = Field(description="Total network received bytes")
    network_sent_bytes: int = Field(description="Total network sent bytes")
    active_connections: int = Field(description="Number of active connections")
    threads_active: int = Field(description="Number of active threads")


class ServiceStatus(BaseModel):
    """Status of a service."""

    service_name: str = Field(description="Service name")
    instance_id: str = Field(description="Service instance ID")
    status: HealthStatus = Field(description="Service health status")
    version: str = Field(description="Service version")
    started_at: str = Field(description="Service start timestamp")
    components: list[ComponentStatus] = Field(default_factory=list, description="Component statuses")
    metrics: SystemMetrics | None = Field(default=None, description="System metrics")


class HealthEvent(IDSBasemodel):
    """Complete health event for MQTT publishing."""

    event_type: Literal["health"] = "health"
    node_id: str = Field(description="Edge node identifier")
    node_type: str = Field(description="Node type (edge, backend)")
    status: HealthStatus = Field(description="Overall health status")
    services: list[ServiceStatus] = Field(default_factory=list, description="Service statuses")
    metrics: SystemMetrics | None = Field(default=None, description="System metrics")
    timestamp: str = Field(description="Event timestamp")


class HealthCheckResponse(BaseModel):
    """Health check API response."""

    status: HealthStatus = Field(description="Overall health status")
    services: list[ComponentStatus] = Field(default_factory=list, description="Service statuses")
    version: str = Field(description="System version")
    timestamp: str = Field(description="Check timestamp")
    details: dict[str, str] | None = Field(default=None, description="Additional details")