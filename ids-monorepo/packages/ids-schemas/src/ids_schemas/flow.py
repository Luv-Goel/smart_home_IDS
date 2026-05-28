"""Flow record schemas for Smart Home IDS.

This module provides Pydantic models for network flow records and features.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from ids_schemas.base import IDSBasemodel


class Protocol(str, Enum):
    """Network protocols."""

    TCP = "TCP"
    UDP = "UDP"
    ICMP = "ICMP"
    HTTP = "HTTP"
    HTTPS = "HTTPS"
    DNS = "DNS"
    ARP = "ARP"
    DHCP = "DHCP"
    MQTT = "MQTT"
    COAP = "COAP"
    UNKNOWN = "UNKNOWN"


class FlowDirection(str, Enum):
    """Flow direction."""

    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


class FlowFeature(BaseModel):
    """Network flow feature vector for ML inference."""

    flow_duration_ms: float = Field(description="Flow duration in milliseconds")
    total_packets: int = Field(description="Total number of packets")
    total_bytes_up: int = Field(description="Total bytes uploaded")
    total_bytes_down: int = Field(description="Total bytes downloaded")
    packets_per_second: float = Field(description="Packets per second")
    bytes_per_second: float = Field(description="Bytes per second")
    avg_packet_size: float = Field(description="Average packet size")
    packet_size_std: float = Field(description="Packet size standard deviation")
    inter_arrival_time_avg: float = Field(description="Average inter-arrival time")
    inter_arrival_time_std: float = Field(description="Inter-arrival time std dev")
    payload_ratio: float = Field(description="Payload to total ratio")
    flags_count: dict[str, int] = Field(default_factory=dict, description="TCP flag counts")
    source_port_category: str = Field(default="ephemeral", description="Source port category")
    destination_port_category: str = Field(default="well_known", description="Destination port category")
    protocol: Protocol = Field(default=Protocol.UNKNOWN, description="Network protocol")
    syn_count: int = Field(default=0, description="SYN packet count")
    ack_count: int = Field(default=0, description="ACK packet count")
    fin_count: int = Field(default=0, description="FIN packet count")
    rst_count: int = Field(default=0, description="RST packet count")
    psh_count: int = Field(default=0, description="PSH packet count")
    urg_count: int = Field(default=0, description="URG packet count")
    window_size_avg: float = Field(default=0.0, description="Average TCP window size")
    payload_entropy: float = Field(default=0.0, description="Payload entropy")


class FlowRecord(IDSBasemodel):
    """Complete flow record with ML features."""

    event_type: Literal["flow"] = "flow"
    node_id: str = Field(description="Edge node identifier")
    flow_id: str = Field(description="Unique flow identifier")
    source_ip: str = Field(description="Source IP address")
    destination_ip: str = Field(description="Destination IP address")
    source_mac: str = Field(description="Source MAC address")
    destination_mac: str = Field(description="Destination MAC address")
    source_port: int = Field(description="Source port")
    destination_port: int = Field(description="Destination port")
    protocol: Protocol = Field(description="Network protocol")
    start_time: str = Field(description="Flow start timestamp")
    end_time: str | None = Field(default=None, description="Flow end timestamp")
    features: FlowFeature = Field(description="Extracted flow features")
    direction: FlowDirection | None = Field(default=None, description="Flow direction")


class FlowEvent(BaseModel):
    """Flow event for processing."""

    event_id: str = Field(description="Unique event identifier")
    flow_record: FlowRecord = Field(description="Flow record")
    timestamp: str = Field(description="Event timestamp")
    source: str = Field(description="Source service")


class FlowQueryParams(BaseModel):
    """Query parameters for flow filtering."""

    source_ip: str | None = Field(default=None, description="Filter by source IP")
    destination_ip: str | None = Field(default=None, description="Filter by destination IP")
    source_port: int | None = Field(default=None, description="Filter by source port")
    destination_port: int | None = Field(default=None, description="Filter by destination port")
    protocol: list[Protocol] | None = Field(default=None, description="Filter by protocol")
    start_time: str | None = Field(default=None, description="Start time filter")
    end_time: str | None = Field(default=None, description="End time filter")
    device_id: str | None = Field(default=None, description="Filter by device MAC")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=1000, description="Records per page")