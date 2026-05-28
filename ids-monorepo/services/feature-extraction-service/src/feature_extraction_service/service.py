"""Feature extraction service for Smart Home IDS.

This module provides the main service class for feature extraction.
"""

import asyncio
import time
from typing import Optional

from ids_core.config import Settings
from ids_core.logger import get_logger
from ids_mqtt.publisher import MQTTPublisher, MQTTConfig
from ids_mqtt.subscriber import MQTTSubscriber

from feature_extraction_service.extractor import FlowState, extract_flow_features


logger = get_logger("feature_extraction.service")


class FeatureExtractionService:
    """Service for extracting features from network packets."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize feature extraction service.

        Args:
            settings: Settings instance (optional)
        """
        self.settings = settings or Settings()
        self._running = False
        self._flows: dict[str, FlowState] = {}
        self._publisher = MQTTPublisher(MQTTConfig.from_settings(settings))
        self._subscriber = MQTTSubscriber(MQTTConfig.from_settings(settings))
        self._logger = logger
        self._packet_count = 0
        self._feature_count = 0

    async def start(self) -> None:
        """Start feature extraction service."""
        self._running = True
        self._logger.info("Starting feature extraction service")

        await self._publisher.start()
        await self._subscriber.subscribe_specific(
            f"ids/edge/{self.settings.node_id}/data/packets",
            self._process_packet,
        )
        self._logger.info("Feature extraction service started")

    async def stop(self) -> None:
        """Stop feature extraction service."""
        self._running = False
        await self._publisher.stop()
        await self._subscriber.stop()
        self._logger.info("Feature extraction service stopped")

    async def _process_packet(self, packet_info: dict) -> None:
        """Process incoming packet information.

        Args:
            packet_info: Packet information dict
        """
        if not self._running:
            return

        try:
            self._packet_count += 1

            # Extract flow key
            src_ip = packet_info.get("src_ip")
            dst_ip = packet_info.get("dst_ip")
            src_port = packet_info.get("src_port", 0)
            dst_port = packet_info.get("dst_port", 0)
            protocol = packet_info.get("protocol", "UNKNOWN")

            flow_key = f"{src_ip}:{src_port}-{dst_ip}:{dst_port}"

            # Update or create flow
            if flow_key in self._flows:
                flow = self._flows[flow_key]
                flow.packets.append(None)  # Placeholder
                flow.bytes_up += packet_info.get("length", 0)
            else:
                flow = FlowState(
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    protocol=protocol,
                    start_time=time.time(),
                    packets=[],
                )
                self._flows[flow_key] = flow

            # Extract features every 10 packets
            if len(flow.packets) >= 10:
                features = extract_flow_features(flow)

                # Publish features
                await self._publisher.publish_json(
                    f"ids/edge/{self.settings.node_id}/data/features",
                    {
                        "flow_key": flow_key,
                        "features": features.model_dump(),
                        "timestamp": time.time(),
                    },
                )

                self._feature_count += 1
                flow.packets = []  # Reset flow

            # Cleanup old flows
            await self._cleanup_flows()

        except Exception as e:
            self._logger.error("Error processing packet", error=str(e))

    async def _cleanup_flows(self) -> None:
        """Cleanup old flows."""
        current_time = time.time()
        flows_to_remove = []

        for key, flow in self._flows.items():
            if current_time - flow.start_time > 300:  # 5 minutes
                flows_to_remove.append(key)

        for key in flows_to_remove:
            del self._flows[key]

    @property
    def packet_count(self) -> int:
        """Get packet count.

        Returns:
            Packet count
        """
        return self._packet_count

    @property
    def feature_count(self) -> int:
        """Get feature count.

        Returns:
            Feature count
        """
        return self._feature_count

    @property
    def active_flows(self) -> int:
        """Get active flow count.

        Returns:
            Active flow count
        """
        return len(self._flows)

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()