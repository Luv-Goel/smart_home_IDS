"""Packet processor for captured packets."""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

from ids_core.logger_enhanced import get_enhanced_logger

from .packet_capturer import CapturedPacket


@dataclass
class ProcessedPacket:
    """Processed packet ready for output."""
    
    packet_id: str  # Unique packet identifier
    captured_packet: CapturedPacket
    processing_time_ms: float
    output_format: str
    output_data: Dict[str, Any] = field(default_factory=dict)
    features: Optional[Dict[str, float]] = None
    
    def to_mqtt_message(self) -> Dict[str, Any]:
        """Convert to MQTT message format.
        
        Returns:
            Dictionary ready for JSON serialization
        """
        message = {
            "packet_id": self.packet_id,
            "node_id": self.captured_packet.metadata.interface,
            "timestamp": datetime.fromtimestamp(
                self.captured_packet.metadata.timestamp
            ).isoformat(),
            "metadata": self.captured_packet.metadata.to_dict(),
            "processing": {
                "processing_time_ms": self.processing_time_ms,
                "output_format": self.output_format,
            }
        }
        
        # Add features if available
        if self.features:
            message["features"] = self.features
        
        # Add packet data if needed
        if self.output_format == "full":
            message["packet_data"] = {
                "raw_hex": self.captured_packet.raw_data.hex(),
                "length": len(self.captured_packet.raw_data),
            }
        
        return message


class PacketProcessor:
    """Process captured packets for output."""
    
    def __init__(self, config):
        """Initialize packet processor.
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.logger = get_enhanced_logger(
            name="processor",
            service_name=config.service_name,
            node_id=config.node_id,
        )
        
        # Statistics
        self.packets_processed = 0
        self.bytes_processed = 0
        self.total_processing_time = 0.0
        self.errors = 0
        
        # Feature extraction cache
        self._feature_cache: Dict[str, Dict[str, float]] = {}
        
        self.logger.info(
            "Packet processor initialized",
            output_format=config.storage_format.value,
            enable_preprocessing=config.enable_preprocessing,
        )
    
    def _generate_packet_id(self, captured_packet: CapturedPacket) -> str:
        """Generate unique packet ID.
        
        Args:
            captured_packet: Captured packet
            
        Returns:
            Unique packet identifier
        """
        # Create hash from packet data and timestamp
        hash_input = (
            captured_packet.raw_data.hex() + 
            str(captured_packet.metadata.timestamp)
        )
        
        packet_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        return f"pkt_{packet_hash}"
    
    def _extract_basic_features(self, captured_packet: CapturedPacket) -> Dict[str, float]:
        """Extract basic features from packet.
        
        Args:
            captured_packet: Captured packet
            
        Returns:
            Dictionary of basic features
        """
        metadata = captured_packet.metadata
        
        features = {
            # Basic packet features
            "packet_length": float(metadata.length),
            "is_tcp": 1.0 if metadata.protocol == "TCP" else 0.0,
            "is_udp": 1.0 if metadata.protocol == "UDP" else 0.0,
            "has_ip": 1.0 if metadata.src_ip else 0.0,
            
            # Port-based features (simplified)
            "src_port": float(metadata.src_port),
            "dst_port": float(metadata.dst_port),
            "is_well_known_port": 1.0 if metadata.dst_port < 1024 else 0.0,
            
            # Protocol-specific flags
            "tcp_syn": float(metadata.flags.get("syn", 0)),
            "tcp_ack": float(metadata.flags.get("ack", 0)),
            "tcp_fin": float(metadata.flags.get("fin", 0)),
            "tcp_rst": float(metadata.flags.get("rst", 0)),
            
            # Statistical features (placeholder)
            "packet_entropy": self._calculate_entropy(captured_packet.raw_data),
        }
        
        # Add more features if IP addresses are available
        if metadata.src_ip and metadata.dst_ip:
            # Simple IP-based features
            features.update({
                "src_ip_class_a": float(self._extract_ip_class(metadata.src_ip, 'a')),
                "dst_ip_class_a": float(self._extract_ip_class(metadata.dst_ip, 'a')),
                "is_local_src": 1.0 if metadata.src_ip.startswith(("192.168.", "10.", "172.")) else 0.0,
                "is_local_dst": 1.0 if metadata.dst_ip.startswith(("192.168.", "10.", "172.")) else 0.0,
            })
        
        return features
    
    def _calculate_entropy(self, data: bytes) -> float:
        """Calculate byte entropy of packet data.
        
        Args:
            data: Packet data bytes
            
        Returns:
            Entropy value (0-8)
        """
        if not data:
            return 0.0
        
        # Calculate byte frequencies
        byte_counts = {}
        for byte in data:
            byte_counts[byte] = byte_counts.get(byte, 0) + 1
        
        # Calculate entropy
        entropy = 0.0
        total_bytes = len(data)
        
        for count in byte_counts.values():
            probability = count / total_bytes
            if probability > 0:
                entropy -= probability * (probability.log() / 2.0.log())
        
        return entropy
    
    def _extract_ip_class(self, ip_address: str, ip_class: str) -> int:
        """Extract IP address class.
        
        Args:
            ip_address: IP address string
            ip_class: Which class to extract ('a', 'b', 'c', 'd')
            
        Returns:
            Integer value of the class octet
        """
        try:
            octets = ip_address.split('.')
            if len(octets) != 4:
                return 0
            
            if ip_class == 'a':
                return int(octets[0])
            elif ip_class == 'b':
                return int(octets[1])
            elif ip_class == 'c':
                return int(octets[2])
            elif ip_class == 'd':
                return int(octets[3])
            else:
                return 0
        except (ValueError, IndexError):
            return 0
    
    def _filter_packet(self, captured_packet: CapturedPacket) -> bool:
        """Filter packet based on configuration.
        
        Args:
            captured_packet: Captured packet
            
        Returns:
            True if packet should be processed, False if filtered out
        """
        metadata = captured_packet.metadata
        
        # Check IP whitelist
        if self.config.ip_whitelist:
            if metadata.src_ip not in self.config.ip_whitelist:
                return False
        
        # Check IP blacklist
        if self.config.ip_blacklist:
            if metadata.src_ip in self.config.ip_blacklist:
                return False
        
        # Check packet size
        if metadata.length > self.config.max_packet_size:
            return False
        
        return True
    
    def _create_output_data(
        self,
        captured_packet: CapturedPacket,
        packet_id: str,
        features: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Create output data dictionary.
        
        Args:
            captured_packet: Captured packet
            packet_id: Unique packet ID
            features: Extracted features
            
        Returns:
            Output data dictionary
        """
        output_format = self.config.storage_format
        
        if output_format.value == "json":
            # JSON format - metadata only
            output_data = {
                "packet_id": packet_id,
                "metadata": captured_packet.metadata.to_dict(),
            }
            
            if features and self.config.extract_features:
                output_data["features"] = features
            
        elif output_format.value == "pcap":
            # PCAP format - binary data
            output_data = {
                "packet_id": packet_id,
                "raw_data": captured_packet.raw_data.hex(),
                "metadata": captured_packet.metadata.to_dict(),
            }
            
        elif output_format.value == "both":
            # Both formats
            output_data = {
                "packet_id": packet_id,
                "raw_data": captured_packet.raw_data.hex(),
                "metadata": captured_packet.metadata.to_dict(),
            }
            
            if features and self.config.extract_features:
                output_data["features"] = features
            
        else:
            # Default to minimal format
            output_data = {
                "packet_id": packet_id,
                "metadata": captured_packet.metadata.to_dict(),
            }
        
        return output_data
    
    async def process_packet(self, captured_packet: CapturedPacket) -> Optional[ProcessedPacket]:
        """Process a single captured packet.
        
        Args:
            captured_packet: Captured packet
            
        Returns:
            Processed packet or None if filtered out
        """
        start_time = time.time()
        
        try:
            # Apply filtering
            if not self._filter_packet(captured_packet):
                return None
            
            # Generate packet ID
            packet_id = self._generate_packet_id(captured_packet)
            
            # Extract features if enabled
            features = None
            if self.config.enable_preprocessing and self.config.extract_features:
                features = self._extract_basic_features(captured_packet)
            
            # Create output data
            output_data = self._create_output_data(captured_packet, packet_id, features)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            # Create processed packet
            processed_packet = ProcessedPacket(
                packet_id=packet_id,
                captured_packet=captured_packet,
                processing_time_ms=processing_time,
                output_format=self.config.storage_format.value,
                output_data=output_data,
                features=features,
            )
            
            # Update statistics
            self.packets_processed += 1
            self.bytes_processed += captured_packet.metadata.length
            self.total_processing_time += processing_time
            
            return processed_packet
            
        except Exception as e:
            self.logger.error(
                "Failed to process packet",
                error=str(e),
                packet_size=len(captured_packet.raw_data) if captured_packet else 0,
            )
            self.errors += 1
            return None
    
    async def process_batch(self, captured_packets: List[CapturedPacket]) -> List[ProcessedPacket]:
        """Process a batch of captured packets.
        
        Args:
            captured_packets: List of captured packets
            
        Returns:
            List of processed packets (filtered)
        """
        processed_packets = []
        
        for captured_packet in captured_packets:
            processed_packet = await self.process_packet(captured_packet)
            if processed_packet:
                processed_packets.append(processed_packet)
        
        return processed_packets
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processor statistics.
        
        Returns:
            Dictionary with statistics
        """
        avg_processing_time = (
            self.total_processing_time / self.packets_processed
            if self.packets_processed > 0 else 0.0
        )
        
        return {
            "packets_processed": self.packets_processed,
            "bytes_processed": self.bytes_processed,
            "total_processing_time_ms": self.total_processing_time,
            "avg_processing_time_ms": avg_processing_time,
            "processing_errors": self.errors,
            "feature_cache_size": len(self._feature_cache),
            "output_format": self.config.storage_format.value,
            "extract_features": self.config.extract_features,
        }