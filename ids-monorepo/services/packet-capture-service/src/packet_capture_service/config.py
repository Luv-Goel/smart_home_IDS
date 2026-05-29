"""Configuration for Packet Capture Service."""

import os
import socket
from typing import List, Optional
from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings


class CaptureMode(Enum):
    """Packet capture modes."""
    ALL = "all"
    FILTERED = "filtered"
    SAMPLED = "sampled"


class PacketStorageFormat(Enum):
    """Packet storage formats."""
    PCAP = "pcap"
    JSON = "json"
    BOTH = "both"


class Config(BaseSettings):
    """Configuration for Packet Capture Service."""
    
    # Service settings
    service_name: str = "packet-capture-service"
    node_id: str = Field(default_factory=lambda: f"pcap-{socket.gethostname()}")
    environment: str = "development"
    
    # Network settings
    network_interface: str = Field(default="eth0")
    capture_mode: CaptureMode = CaptureMode.FILTERED
    promiscuous_mode: bool = False
    buffer_size: int = 65536  # Packet buffer size
    
    # Filter settings
    bpf_filter: str = "not port 22"  # BPF filter string
    ip_whitelist: Optional[List[str]] = None
    ip_blacklist: Optional[List[str]] = None
    
    # Capture settings
    packet_batch_size: int = 100
    max_packets_per_batch: int = 1000
    max_packet_size: int = 1514  # Standard Ethernet MTU
    
    # Storage settings
    storage_format: PacketStorageFormat = PacketStorageFormat.JSON
    output_directory: str = "/var/pcap"
    rotate_interval: int = 3600  # Rotate files every hour
    max_file_size_mb: int = 100
    
    # Processing settings
    enable_preprocessing: bool = True
    extract_features: bool = False  # Basic feature extraction
    
    # MQTT settings
    mqtt_broker_url: str = "mqtt://localhost:1883"
    mqtt_client_id: str = Field(default_factory=lambda: f"pcap-{os.getpid()}")
    mqtt_packet_topic: str = "ids/edge/+/packets"
    mqtt_status_topic: str = "ids/edge/+/pcap/status"
    mqtt_qos: int = 0  # QoS 0 for high-throughput packet data
    
    # Performance settings
    max_queue_size: int = 10000
    processing_threads: int = 2
    stats_interval: int = 60  # Statistics logging interval in seconds
    
    # Edge optimization
    optimize_for_edge: bool = False
    max_cpu_percent: int = 30
    max_memory_mb: int = 256
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        env_prefix = "PCAP_"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        """Initialize config with optimizations."""
        super().__init__(**kwargs)
        
        if self.optimize_for_edge:
            self._apply_edge_optimizations()
    
    def _apply_edge_optimizations(self):
        """Apply optimizations for edge devices."""
        self.packet_batch_size = 50
        self.max_queue_size = 1000
        self.processing_threads = 1
        self.max_memory_mb = 128
        self.storage_format = PacketStorageFormat.JSON  # JSON is lighter than PCAP
        self.mqtt_qos = 0  # Lower QoS for edge
    
    @property
    def is_valid_interface(self) -> bool:
        """Check if network interface is valid."""
        # Simple check - in production would check system interfaces
        return bool(self.network_interface)
    
    @property
    def full_packet_topic(self) -> str:
        """Get full packet topic with node ID."""
        return self.mqtt_packet_topic.replace("+", self.node_id)
    
    @property
    def full_status_topic(self) -> str:
        """Get full status topic with node ID."""
        return self.mqtt_status_topic.replace("+", self.node_id)


# Global config instance
config = Config()