"""MQTT subscriber for Smart Home IDS.

This module provides a subscriber class that handles event subscription
with automatic reconnection and message processing.
"""

import asyncio
import json
from typing import Any, Awaitable, Callable, Optional
from dataclasses import dataclass
from functools import wraps

from ids_core.config import Settings
from ids_core.logger import get_logger
from ids_mqtt.client import MQTTClient, MQTTConfig
from ids_mqtt.topic import MQTTEdgeTopic, MQTTHubTopic


logger = get_logger("ids_mqtt.subscriber")


class MQTTSubscriber:
    """MQTT subscriber with automatic topic registration."""

    def __init__(self, config: Optional[MQTTConfig] = None, settings: Optional[Settings] = None):
        """Initialize subscriber.

        Args:
            config: MQTT configuration (optional)
            settings: Settings instance (optional)
        """
        self.config = config or MQTTConfig.from_settings(settings or Settings())
        self.client = MQTTClient(self.config)
        self._running = False
        self._handlers = {}
        self._logger = logger

    async def start(self) -> None:
        """Start the subscriber."""
        await self.client.start()
        self._running = True

        # Register default subscriptions
        await self.subscribe_alerts()
        await self.subscribe_status()
        await self.subscribe_config()

        self._logger.info("MQTT Subscriber started")

    async def stop(self) -> None:
        """Stop the subscriber."""
        self._running = False
        await self.client.stop()
        self._logger.info("MQTT Subscriber stopped")

    async def subscribe_alerts(self) -> bool:
        """Subscribe to alert topics.

        Returns:
            True if successful
        """
        topics = [
            MQTTHubTopic.ALERTS.value,
            MQTTEdgeTopic.ALERTS_CRITICAL.value,
            MQTTEdgeTopic.ALERTS_HIGH.value,
            MQTTEdgeTopic.ALERTS_MEDIUM.value,
            MQTTEdgeTopic.ALERTS_LOW.value,
            MQTTEdgeTopic.ALERTS_INFO.value,
        ]

        for topic in topics:
            await self.client.subscribe(topic, self._default_handler)

        return True

    async def subscribe_status(self) -> bool:
        """Subscribe to status topics.

        Returns:
            True if successful
        """
        topics = [
            MQTTHubTopic.STATUS.value,
            MQTTEdgeTopic.STATUS_HEALTH.value,
        ]

        for topic in topics:
            await self.client.subscribe(topic, self._default_handler)

        return True

    async def subscribe_config(self) -> bool:
        """Subscribe to config topics.

        Returns:
            True if successful
        """
        topics = [
            MQTTHubTopic.CONFIG.value,
        ]

        for topic in topics:
            await self.client.subscribe(topic, self._default_handler)

        return True

    async def subscribe_specific(self, topic: str, handler: Callable[[dict], Awaitable[None]]) -> bool:
        """Subscribe to a specific topic with a custom handler.

        Args:
            topic: Topic to subscribe to
            handler: Async handler function

        Returns:
            True if successful
        """
        # Register handler
        self._handlers[topic] = handler

        # Subscribe
        return await self.client.subscribe(topic, handler)

    async def unsubscribe_specific(self, topic: str) -> bool:
        """Unsubscribe from a specific topic.

        Args:
            topic: Topic to unsubscribe from

        Returns:
            True if successful
        """
        # Unsubscribe
        result = await self.client.unsubscribe(topic)

        # Remove handler
        if topic in self._handlers:
            del self._handlers[topic]

        return result

    async def _default_handler(self, message: dict[str, Any]) -> None:
        """Default message handler.

        Args:
            message: Message payload
        """
        event_type = message.get("event_type", "unknown")
        self._logger.debug("Received message", event_type=event_type, message=message)

        # Route to specific handler if available
        if event_type in self._handlers:
            await self._handlers[event_type](message)

    async def handle_alert(self, message: dict[str, Any]) -> None:
        """Handle alert messages.

        Args:
            message: Alert message payload
        """
        self._logger.info("Processing alert", alert_type=message.get("alert_type"))

    async def handle_status(self, message: dict[str, Any]) -> None:
        """Handle status messages.

        Args:
            message: Status message payload
        """
        self._logger.info("Processing status", node_id=message.get("node_id"))

    async def handle_config(self, message: dict[str, Any]) -> None:
        """Handle configuration messages.

        Args:
            message: Config message payload
        """
        self._logger.info("Processing config update", config=message.get("config"))

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()