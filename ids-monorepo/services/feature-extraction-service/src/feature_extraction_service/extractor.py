"""Feature extractor for network flows.

This module provides feature extraction functionality
from network packets.
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from scapy.all import Packet, IP, TCP, UDP

from ids_schemas.flow import FlowFeature, Protocol, FlowDirection


@dataclass
class FlowState:
    """State of a network flow."""

    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    start_time: float
    packets: List[Packet] = None
    bytes_up: int = 0
    bytes_down: int = 0

    def __post_init__(self):
        """Initialize packets list."""
        if self.packets is None:
            self.packets = []



def extract_flow_features(flow: FlowState) -> FlowFeature:
    """Extract features from flow state.

    Args:
        flow: Flow state

    Returns:
        FlowFeature instance
    """
    packets = flow.packets
    packet_count = len(packets)

    if packet_count == 0:
        return FlowFeature(
            flow_duration_ms=0,
            total_packets=0,
            total_bytes_up=0,
            total_bytes_down=0,
            packets_per_second=0,
            bytes_per_second=0,
            avg_packet_size=0,
            packet_size_std=0,
            inter_arrival_time_avg=0,
            inter_arrival_time_std=0,
            payload_ratio=0,
            flags_count={},
            source_port_category="unknown",
            destination_port_category="unknown",
            protocol=Protocol.UNKNOWN,
            syn_count=0,
            ack_count=0,
            fin_count=0,
            rst_count=0,
            psh_count=0,
            urg_count=0,
            window_size_avg=0,
            payload_entropy=0,
        )

    # Calculate flow duration
    timestamps = [p.time for p in packets]
    flow_duration_ms = (max(timestamps) - min(timestamps)) * 1000

    # Calculate byte counts
    total_bytes_up = flow.bytes_up
    total_bytes_down = flow.bytes_down

    # Calculate packet statistics
    packet_sizes = [len(p) for p in packets]
    avg_packet_size = sum(packet_sizes) / len(packet_sizes)
    packet_size_std = (
        sum((x - avg_packet_size) ** 2 for x in packet_sizes) / len(packet_sizes)
    ) ** 0.5

    # Calculate timing statistics
    inter_arrival_times = [
        timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)
    ]
    inter_arrival_time_avg = (
        sum(inter_arrival_times) / len(inter_arrival_times)
        if inter_arrival_times
        else 0
    )
    inter_arrival_time_std = (
        sum((x - inter_arrival_time_avg) ** 2 for x in inter_arrival_times)
        / len(inter_arrival_times)
        if inter_arrival_times
        else 0
    ) ** 0.5

    # Calculate rates
    duration_seconds = flow_duration_ms / 1000
    packets_per_second = packet_count / duration_seconds if duration_seconds > 0 else 0
    bytes_per_second = (total_bytes_up + total_bytes_down) / duration_seconds if duration_seconds > 0 else 0

    # Calculate payload ratio
    payload_bytes = sum(len(p) - (p[IP].ihl * 4) for p in packets if IP in p)
    total_bytes = sum(len(p) for p in packets)
    payload_ratio = payload_bytes / total_bytes if total_bytes > 0 else 0

    # Calculate TCP flag counts
    flags_count = {
        "SYN": 0,
        "ACK": 0,
        "FIN": 0,
        "RST": 0,
        "PSH": 0,
        "URG": 0,
    }
    for p in packets:
        if TCP in p:
            tcp_flags = str(p[TCP].flags)
            if "S" in tcp_flags:
                flags_count["SYN"] += 1
            if "A" in tcp_flags:
                flags_count["ACK"] += 1
            if "F" in tcp_flags:
                flags_count["FIN"] += 1
            if "R" in tcp_flags:
                flags_count["RST"] += 1
            if "P" in tcp_flags:
                flags_count["PSH"] += 1
            if "U" in tcp_flags:
                flags_count["URG"] += 1

    # Determine port categories
    source_port_category = _get_port_category(flow.src_port)
    destination_port_category = _get_port_category(flow.dst_port)

    # Get protocol
    protocol = Protocol(flow.protocol.upper()) if flow.protocol.upper() in [p.value for p in Protocol] else Protocol.UNKNOWN

    return FlowFeature(
        flow_duration_ms=flow_duration_ms,
        total_packets=packet_count,
        total_bytes_up=total_bytes_up,
        total_bytes_down=total_bytes_down,
        packets_per_second=packets_per_second,
        bytes_per_second=bytes_per_second,
        avg_packet_size=avg_packet_size,
        packet_size_std=packet_size_std,
        inter_arrival_time_avg=inter_arrival_time_avg,
        inter_arrival_time_std=inter_arrival_time_std,
        payload_ratio=payload_ratio,
        flags_count=flags_count,
        source_port_category=source_port_category,
        destination_port_category=destination_port_category,
        protocol=protocol,
        syn_count=flags_count["SYN"],
        ack_count=flags_count["ACK"],
        fin_count=flags_count["FIN"],
        rst_count=flags_count["RST"],
        psh_count=flags_count["PSH"],
        urg_count=flags_count["URG"],
        window_size_avg=0,  # Would need actual window sizes
        payload_entropy=0,  # Would need entropy calculation
    )


def _get_port_category(port: int) -> str:
    """Get port category.

    Args:
        port: Port number

    Returns:
        Port category
    """
    if port < 1024:
        return "well_known"
    elif port < 49152:
        return "registered"
    else:
        return "ephemeral"