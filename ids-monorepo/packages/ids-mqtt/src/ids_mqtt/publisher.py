"""MQTT publisher for Smart Home IDS.

This module provides a publisher class that handles event publishing
with automatic reconnection and error handling.
"""

import asyncio
import json
from typing import Any, Optional
from dataclasses import dataclass

from ids_core.config import Settings
from ids_core.logger import get_logger
from ids_mqtt.client import MQTTClient, MQTTConfig
from ids_mqtt.topic import TopicRegistry, MQTTEdgeTopic, MQTTHubTopic


logger = get_logger("ids_mqtt.publisher")


class MQTTPublisher:
    """MQTT publisher with reliability features."""

    def __init__(self, config: Optional[MQTTConfig] = None, settings: Optional[Settings] = None):
        """Initialize publisher.

        Args:
            config: MQTT configuration (optional)
            settings: Settings instance (optional)
        """
        self.config = config or MQTTConfig.from_settings(settings or Settings())
        self.client = MQTTClient(self.config)
        self.topic_registry = TopicRegistry()
        self._running = False
        self._batch_buffer = []
        self._max_batch_size = 100
        self._batch_interval = 5.0
        self._batch_task = None
        self._logger = logger

    async def start(self) -> None:
        """Start the publisher."""
        await self.client.start()
        self._running = True
        self._batch_task = asyncio.create_task(self._process_batch())
        self._logger.info("MQTT Publisher started")

    async def stop(self) -> None:
        """Stop the publisher."""
        self._running = False

        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass

        await self.client.stop()
        self._logger.info("MQTT Publisher stopped")

    async def publish_alert(
        self,
        node_id: str,
        alert_type: str,
        category: str,
        severity: str,
        confidence: float,
        device_id: str,
        device_ip: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Publish an alert event.

        Args:
            node_id: Edge node identifier
            alert_type: Type of alert
            category: Alert category
            severity: Alert severity
            confidence: Confidence score
            device_id: Device identifier
            device_ip: Device IP address (optional)
            payload: Additional payload (optional)

        Returns:
            True if successful
        """
        message = {
            "event_type": "alert",
            "node_id": node_id,
            "device_id": device_id,
            "device_ip": device_ip,
            "payload": {
                "alert_type": alert_type,
                "category": category,
                "severity": severity,
                "confidence_score": confidence,
                "timestamp": payload.get("timestamp") if payload else None,
            },
            "timestamp": payload.get("timestamp") if payload else None,
        }

        topic = MQTTEdgeTopic.ALERTS_CRITICAL.format(node_id=node_id)
        return await self._publish(topic, message)

    async def publish_device(
        self,
        node_id: str,
        state: str,
        mac_address: str,
        ip_address: Optional[str] = None,
        device_type: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Publish a device event.

        Args:
            node_id: Edge node identifier
            state: Device state
            mac_address: Device MAC address
            ip_address: Device IP address (optional)
            device_type: Device type (optional)
            payload: Additional payload (optional)

        Returns:
            True if successful
        """
        message = {
            "event_type": "device",
            "node_id": node_id,
            "payload": {
                "mac_address": mac_address,
                "ip_address": ip_address,
                "device_type": device_type,
                "state": state,
            },
            "timestamp": payload.get("timestamp") if payload else None,
        }

        topic = MQTTEdgeTopic.STATUS_HEALTH.format(node_id=node_id)
        return await self._publish(topic, message)

    async def publish_health(
        self,
        node_id: str,
        status: str,
        metrics: Optional[dict[str, Any]] = None,
        services: Optional[list[dict[str, Any]]] = None,
    ) -> bool:
        """Publish system health status.

        Args:
            node_id: Edge node identifier
            status: Health status
            metrics: System metrics (optional)
            services: Service statuses (optional)

        Returns:
            True if successful
        """
        message = {
            "event_type": "health",
            "node_id": node_id,
            "node_type": "edge",
            "status": status,
            "metrics": metrics or {},
            "services": services or [],
            "timestamp": None,
        }

        topic = MQTTHubTopic.HEARTBEAT.value
        return await self._publish(topic, message)

    async def publish_inference(
        self,
        node_id: str,
        flow_id: str,
        result: dict[str, Any],
        feature_vector: dict[str, float],
    ) -> bool:
        """Publish inference result.

        Args:
            node_id: Edge node identifier
            flow_id: Flow identifier
            result: Inference result
            feature_vector: Feature vector used

        Returns:
            True if successful
        """
        message = {
            "event_type": "inference",
            "node_id": node_id,
            "flow_id": flow_id,
            "result": result,
            "feature_vector": feature_vector,
            "timestamp": None,
        }

        topic = MQTTEdgeTopic.DATA_INFERENCE.format(node_id=node_id)
        return await self._publish(topic, message)

    async def publish_flow(
        self,
        node_id: str,
        flow_id: str,
        source_ip: str,
        destination_ip: str,
        source_mac: str,
        destination_mac: str,
        source_port: int,
        destination_port: int,
        protocol: str,
        features: dict[str, Any],
    ) -> bool:
        """Publish flow record.

        Args:
            node_id: Edge node identifier
            flow_id: Flow identifier
            source_ip: Source IP address
            destination_ip: Destination IP address
            source_mac: Source MAC address
            destination_mac: Destination MAC address
            source_port: Source port
            destination_port: Destination port
            protocol: Network protocol
            features: Flow features

        Returns:
            True if successful
        """
        message = {
            "event_type": "flow",
            "node_id": node_id,
            "flow_id": flow_id,
            "source_ip": source_ip,
            "destination_ip": destination_ip,
            "source_mac": source_mac,
            "destination_mac": destination_mac,
            "source_port": source_port,
            "destination_port": destination_port,
            "protocol": protocol,
            "features": features,
            "timestamp": None,
        }

        topic = MQTTEdgeTopic.DATA_FLOW.format(node_id=node_id)
        return await self._publish(topic, message)

    async def _publish(self, topic: str, message: dict[str, Any]) -> bool:
        """Publish a message to a topic.

        Args:
            topic: Topic to publish to
            message: Message payload

        Returns:
            True if successful
        """
        try:
            if not self.client.is_connected:
                self._logger.warning("MQTT client not connected, buffering message")
                self._batch_buffer.append((topic, message))
                return True

            result = await self.client.publish(topic, message)
            if not result:
                self._logger.error("Failed to publish message", topic=topic)
                return False
            return True
        except Exception as e:
            self._logger.error("Error publishing message", topic=topic, error=str(e))
            return False

    async def _process_batch(self) -> None:
        """Process batch buffer."""
        while self._running:
            try:
                if len(self._batch_buffer) >= self._max_batch_size or (
                    len(self._batch_buffer) > 0 and self.client.is_connected
                ):
                    while self._batch_buffer and self.client.is_connected:
                        topic, message = self._batch_buffer.pop(0)
                        await self._publish(topic, message)
                await asyncio.sleep(self._batch_interval)
            except Exception as e:
                self._logger.error("Error processing batch", error=str(e))
                await asyncio.sleep(1.0)

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()