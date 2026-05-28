"""Packet capture service for Smart Home IDS.

This module provides packet capture functionality using Scapy.
"""

import asyncio
import time
from typing import Optional

from scapy.all import sniff, AsyncSniffer, IP, TCP, UDP, ARP
from scapy.packet import Packet

from ids_core.config import Settings
from ids_core.logger import get_logger
from ids_mqtt.publisher import MQTTPublisher, MQTTConfig


logger = get_logger("packet_capture.service")


class PacketCaptureService:
    """Service for capturing network packets."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize packet capture service.

        Args:
            settings: Settings instance (optional)
        """
        self.settings = settings or Settings()
        self._running = False
        self._sniffer: Optional[AsyncSniffer] = None
        self._packet_count = 0
        self._start_time = None
        self._publisher = MQTTPublisher(MQTTConfig.from_settings(settings))
        self._logger = logger

    async def start(self) -> None:
        """Start packet capture service."""
        self._running = True
        self._start_time = time.time()
        self._logger.info(
            "Starting packet capture service",
            interface=self.settings.network_interface,
        )

        await self._publisher.start()
        self._sniffer = AsyncSniffer(
            iface=self.settings.network_interface,
            prn=self._process_packet,
            store=False,
        )
        self._sniffer.start()
        self._logger.info("Packet capture service started")

    async def stop(self) -> None:
        """Stop packet capture service."""
        self._running = False
        if self._sniffer:
            self._sniffer.stop()
        await self._publisher.stop()
        self._logger.info("Packet capture service stopped")

    def _process_packet(self, packet: Packet) -> None:
        """Process captured packet.

        Args:
            packet: Scapy packet
        """
        if not self._running:
            return

        try:
            self._packet_count += 1

            # Extract packet information
            packet_info = {
                "timestamp": time.time(),
                "length": len(packet),
                "protocol": self._get_protocol(packet),
                "src_ip": self._get_src_ip(packet),
                "dst_ip": self._get_dst_ip(packet),
                "src_mac": self._get_src_mac(packet),
                "dst_mac": self._get_dst_mac(packet),
                "src_port": self._get_src_port(packet),
                "dst_port": self._get_dst_port(packet),
            }

            # Publish packet info
            asyncio.run_coroutine_threadsafe(
                self._publisher.publish_raw(
                    f"ids/edge/{self.settings.node_id}/data/packets",
                    str(packet_info).encode(),
                ),
                asyncio.get_event_loop(),
            )

        except Exception as e:
            self._logger.error("Error processing packet", error=str(e))

    def _get_protocol(self, packet: Packet) -> str:
        """Get packet protocol.

        Args:
            packet: Scapy packet

        Returns:
            Protocol name
        """
        if IP in packet:
            if packet[IP].proto == 6:
                return "TCP"
            elif packet[IP].proto == 17:
                return "UDP"
            elif packet[IP].proto == 1:
                return "ICMP"
        return "UNKNOWN"

    def _get_src_ip(self, packet: Packet) -> Optional[str]:
        """Get source IP address.

        Args:
            packet: Scapy packet

        Returns:
            Source IP address
        """
        if IP in packet:
            return packet[IP].src
        return None

    def _get_dst_ip(self, packet: Packet) -> Optional[str]:
        """Get destination IP address.

        Args:
            packet: Scapy packet

        Returns:
            Destination IP address
        """
        if IP in packet:
            return packet[IP].dst
        return None

    def _get_src_mac(self, packet: Packet) -> Optional[str]:
        """Get source MAC address.

        Args:
            packet: Scapy packet

        Returns:
            Source MAC address
        """
        if ARP in packet:
            return packet[ARP].hwsrc
        elif hasattr(packet, "src"):
            return packet.src
        return None

    def _get_dst_mac(self, packet: Packet) -> Optional[str]:
        """Get destination MAC address.

        Args:
            packet: Scapy packet

        Returns:
            Destination MAC address
        """
        if ARP in packet:
            return packet[ARP].hwdst
        elif hasattr(packet, "dst"):
            return packet.dst
        return None

    def _get_src_port(self, packet: Packet) -> Optional[int]:
        """Get source port.

        Args:
            packet: Scapy packet

        Returns:
            Source port
        """
        if TCP in packet or UDP in packet:
            transport_layer = packet[TCP] if TCP in packet else packet[UDP]
            return transport_layer.sport
        return None

    def _get_dst_port(self, packet: Packet) -> Optional[int]:
        """Get destination port.

        Args:
            packet: Scapy packet

        Returns:
            Destination port
        """
        if TCP in packet or UDP in packet:
            transport_layer = packet[TCP] if TCP in packet else packet[UDP]
            return transport_layer.dport
        return None

    @property
    def packet_count(self) -> int:
        """Get packet count.

        Returns:
            Packet count
        """
        return self._packet_count

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds.

        Returns:
            Uptime in seconds
        """
        if self._start_time:
            return time.time() - self._start_time
        return 0

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()