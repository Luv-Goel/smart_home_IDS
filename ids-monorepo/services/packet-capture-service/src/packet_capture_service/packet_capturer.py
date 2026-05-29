"""Packet capturer using Scapy/PyShark."""

import asyncio
import time
import threading
import queue
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import json

try:
    from scapy.all import sniff, Ether, IP, TCP, UDP, conf, get_if_list
    from scapy.error import Scapy_Exception
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    print("Warning: Scapy not available, using dummy mode")

from ids_core.logger_enhanced import get_enhanced_logger


@dataclass
class PacketMetadata:
    """Metadata for a captured packet."""
    
    timestamp: float
    interface: str
    length: int
    captured_length: int
    protocol: str = ""
    src_ip: str = ""
    dst_ip: str = ""
    src_port: int = 0
    dst_port: int = 0
    flags: Dict[str, bool] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "interface": self.interface,
            "length": self.length,
            "captured_length": self.captured_length,
            "protocol": self.protocol,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "flags": self.flags,
        }


@dataclass
class CapturedPacket:
    """A captured packet with metadata."""
    
    raw_data: bytes
    metadata: PacketMetadata
    
    def __post_init__(self):
        """Validate packet."""
        if not self.raw_data:
            raise ValueError("Packet has no data")
        if not isinstance(self.raw_data, bytes):
            self.raw_data = bytes(self.raw_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "raw_data": self.raw_data.hex(),
            "metadata": self.metadata.to_dict(),
        }


class PacketCapturer:
    """Async packet capturer using Scapy."""
    
    def __init__(self, config):
        """Initialize packet capturer.
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.logger = get_enhanced_logger(
            name="capturer",
            service_name=config.service_name,
            node_id=config.node_id,
        )
        
        # State
        self.running = False
        self.capture_thread: Optional[threading.Thread] = None
        self.packet_queue: queue.Queue = queue.Queue(maxsize=config.max_queue_size)
        
        # Statistics
        self.packets_captured = 0
        self.bytes_captured = 0
        self.errors = 0
        self.last_stats_time = time.time()
        
        # Performance tracking
        self.avg_packet_rate = 0.0
        self.avg_byte_rate = 0.0
        
        self.logger.info(
            "Packet capturer initialized",
            interface=config.network_interface,
            capture_mode=config.capture_mode.value,
            scapy_available=SCAPY_AVAILABLE,
        )
    
    async def start(self):
        """Start packet capture."""
        if not SCAPY_AVAILABLE:
            self.logger.error("Scapy not available, cannot capture packets")
            return False
        
        if not self.config.is_valid_interface:
            self.logger.error("Invalid network interface")
            return False
        
        if self.running:
            self.logger.warning("Packet capture already running")
            return True
        
        self.logger.info("Starting packet capture", interface=self.config.network_interface)
        self.running = True
        
        # Start capture thread
        self.capture_thread = threading.Thread(
            target=self._capture_loop,
            name="packet-capture-thread",
            daemon=True,
        )
        self.capture_thread.start()
        
        # Start statistics logging
        asyncio.create_task(self._log_statistics())
        
        self.logger.info("Packet capture started")
        return True
    
    async def stop(self):
        """Stop packet capture."""
        self.logger.info("Stopping packet capture")
        self.running = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=5.0)
            self.capture_thread = None
        
        # Clear queue
        while not self.packet_queue.empty():
            try:
                self.packet_queue.get_nowait()
            except queue.Empty:
                break
        
        self.logger.info("Packet capture stopped")
    
    def _capture_loop(self):
        """Main capture loop running in background thread."""
        self.logger.info("Starting capture loop")
        
        try:
            # Configure Scapy
            conf.iface = self.config.network_interface
            conf.promisc = self.config.promiscuous_mode
            
            # Start sniffing
            sniff(
                iface=self.config.network_interface,
                prn=self._process_packet,
                store=False,  # Don't store packets in memory
                filter=self.config.bpf_filter,
                count=0,  # Capture indefinitely
                promisc=self.config.promiscuous_mode,
            )
            
        except Scapy_Exception as e:
            self.logger.error("Scapy capture error", error=str(e))
            self.errors += 1
        except Exception as e:
            self.logger.error("Unexpected capture error", error=str(e))
            self.errors += 1
    
    def _process_packet(self, packet):
        """Process captured packet (called by Scapy).
        
        Args:
            packet: Scapy packet object
        """
        if not self.running:
            return
        
        try:
            # Extract metadata
            metadata = self._extract_packet_metadata(packet)
            
            # Create captured packet
            captured_packet = CapturedPacket(
                raw_data=bytes(packet),
                metadata=metadata,
            )
            
            # Add to queue
            try:
                self.packet_queue.put_nowait(captured_packet)
                
                # Update statistics
                self.packets_captured += 1
                self.bytes_captured += metadata.length
                
            except queue.Full:
                self.logger.warning("Packet queue full, dropping packet")
                
        except Exception as e:
            self.logger.warning("Failed to process packet", error=str(e))
            self.errors += 1
    
    def _extract_packet_metadata(self, packet) -> PacketMetadata:
        """Extract metadata from Scapy packet.
        
        Args:
            packet: Scapy packet object
            
        Returns:
            Packet metadata
        """
        current_time = time.time()
        
        # Basic metadata
        metadata = PacketMetadata(
            timestamp=current_time,
            interface=self.config.network_interface,
            length=len(packet),
            captured_length=len(packet),
        )
        
        try:
            # Extract Ethernet layer
            if packet.haslayer(Ether):
                eth_layer = packet[Ether]
                # Could extract MAC addresses here
            
            # Extract IP layer
            if packet.haslayer(IP):
                ip_layer = packet[IP]
                metadata.src_ip = ip_layer.src
                metadata.dst_ip = ip_layer.dst
                metadata.protocol = "IP"
                
                # Check for TCP
                if packet.haslayer(TCP):
                    tcp_layer = packet[TCP]
                    metadata.protocol = "TCP"
                    metadata.src_port = tcp_layer.sport
                    metadata.dst_port = tcp_layer.dport
                    
                    # Extract TCP flags
                    metadata.flags = {
                        "syn": bool(tcp_layer.flags & 0x02),
                        "ack": bool(tcp_layer.flags & 0x10),
                        "fin": bool(tcp_layer.flags & 0x01),
                        "rst": bool(tcp_layer.flags & 0x04),
                        "psh": bool(tcp_layer.flags & 0x08),
                        "urg": bool(tcp_layer.flags & 0x20),
                    }
                    
                # Check for UDP
                elif packet.haslayer(UDP):
                    udp_layer = packet[UDP]
                    metadata.protocol = "UDP"
                    metadata.src_port = udp_layer.sport
                    metadata.dst_port = udp_layer.dport
            
        except Exception as e:
            self.logger.debug("Failed to extract packet details", error=str(e))
        
        return metadata
    
    async def get_packet_batch(self, max_wait: float = 1.0) -> List[CapturedPacket]:
        """Get a batch of captured packets.
        
        Args:
            max_wait: Maximum wait time in seconds
            
        Returns:
            List of captured packets
        """
        batch = []
        batch_size = 0
        
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait and batch_size < self.config.packet_batch_size:
            try:
                # Try to get packet with short timeout
                packet = self.packet_queue.get(timeout=0.1)
                batch.append(packet)
                batch_size += 1
                
            except queue.Empty:
                # No packets available, continue waiting
                await asyncio.sleep(0.01)
                continue
        
        return batch
    
    async def _log_statistics(self):
        """Periodically log capture statistics."""
        while self.running:
            await asyncio.sleep(self.config.stats_interval)
            
            current_time = time.time()
            elapsed = current_time - self.last_stats_time
            
            if elapsed > 0:
                packet_rate = self.packets_captured / elapsed
                byte_rate = self.bytes_captured / elapsed
                
                # Update averages with exponential smoothing
                self.avg_packet_rate = 0.9 * self.avg_packet_rate + 0.1 * packet_rate
                self.avg_byte_rate = 0.9 * self.avg_byte_rate + 0.1 * byte_rate
                
                self.logger.info(
                    "Capture statistics",
                    packets_captured=self.packets_captured,
                    bytes_captured=self.bytes_captured,
                    packet_rate=packet_rate,
                    avg_packet_rate=self.avg_packet_rate,
                    byte_rate=byte_rate,
                    avg_byte_rate=self.avg_byte_rate,
                    queue_size=self.packet_queue.qsize(),
                    queue_max=self.packet_queue.maxsize,
                    queue_usage=f"{(self.packet_queue.qsize() / self.packet_queue.maxsize) * 100:.1f}%",
                    errors=self.errors,
                )
                
                # Reset counters
                self.packets_captured = 0
                self.bytes_captured = 0
                self.last_stats_time = current_time
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics.
        
        Returns:
            Dictionary with statistics
        """
        current_time = time.time()
        elapsed = current_time - self.last_stats_time if self.last_stats_time > 0 else 0
        
        return {
            "running": self.running,
            "queue_size": self.packet_queue.qsize(),
            "queue_max": self.packet_queue.maxsize,
            "queue_usage_percent": (self.packet_queue.qsize() / self.packet_queue.maxsize) * 100,
            "avg_packet_rate": self.avg_packet_rate,
            "avg_byte_rate": self.avg_byte_rate,
            "total_errors": self.errors,
            "capture_time_seconds": elapsed,
            "interface": self.config.network_interface,
            "thread_alive": bool(self.capture_thread and self.capture_thread.is_alive()),
        }


class DummyPacketCapturer(PacketCapturer):
    """Dummy packet capturer for testing when Scapy is not available."""
    
    def __init__(self, config):
        """Initialize dummy capturer."""
        super().__init__(config)
        self.logger.warning("Using dummy packet capturer - no real packets will be captured")
    
    def _capture_loop(self):
        """Dummy capture loop."""
        self.logger.info("Starting dummy capture loop")
        
        packet_counter = 0
        
        while self.running:
            # Simulate packet capture
            time.sleep(0.1)  # Simulate network delay
            
            packet_counter += 1
            
            # Generate dummy packet every 10 iterations
            if packet_counter % 10 == 0:
                metadata = PacketMetadata(
                    timestamp=time.time(),
                    interface=self.config.network_interface,
                    length=100,
                    captured_length=100,
                    protocol="TCP",
                    src_ip="192.168.1.100",
                    dst_ip="192.168.1.1",
                    src_port=54321,
                    dst_port=80,
                    flags={"syn": True, "ack": False},
                )
                
                # Create dummy packet data
                dummy_data = bytes([i % 256 for i in range(100)])
                
                captured_packet = CapturedPacket(
                    raw_data=dummy_data,
                    metadata=metadata,
                )
                
                try:
                    self.packet_queue.put_nowait(captured_packet)
                    
                    # Update statistics
                    self.packets_captured += 1
                    self.bytes_captured += metadata.length
                    
                except queue.Full:
                    pass
    
    async def start(self):
        """Start dummy capture."""
        self.logger.info("Starting dummy packet capture")
        self.running = True
        
        # Start capture thread
        self.capture_thread = threading.Thread(
            target=self._capture_loop,
            name="dummy-capture-thread",
            daemon=True,
        )
        self.capture_thread.start()
        
        # Start statistics logging
        asyncio.create_task(self._log_statistics())
        
        self.logger.info("Dummy packet capture started")
        return True


def create_packet_capturer(config) -> PacketCapturer:
    """Factory function to create packet capturer.
    
    Args:
        config: Service configuration
        
    Returns:
        Packet capturer instance
    """
    if SCAPY_AVAILABLE:
        return PacketCapturer(config)
    else:
        return DummyPacketCapturer(config)