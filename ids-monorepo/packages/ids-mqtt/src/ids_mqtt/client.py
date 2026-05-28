"""MQTT client wrapper for Smart Home IDS.

This module provides an async MQTT client with connection management,
reconnection logic, and message handling.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from paho.mqtt.enums import MQTTv5

from ids_core.config import Settings
from ids_core.logger import get_logger


logger = get_logger("ids_mqtt.client")


@dataclass
class MQTTConfig:
    """MQTT client configuration."""

    broker_url: str
    port: int = 1883
    client_id: str = "ids-client"
    keepalive: int = 60
    clean_session: bool = True
   username: Optional[str] = None
    password: Optional[str] = None
    ca_certs: Optional[str] = None
    certfile: Optional[str] = None
    keyfile: Optional[str] = None
    tls_insecure: bool = False
    version: int = MQTTv5

    @classmethod
    def from_settings(cls, settings: Settings) -> "MQTTConfig":
        """Create config from settings.

        Args:
            settings: Settings instance

        Returns:
            MQTTConfig instance
        """
        # Parse broker URL to extract host and port
        broker_url = settings.mqtt_broker_url
        if broker_url.startswith("mqtt://"):
            host = broker_url.replace("mqtt://", "")
            port = 1883
        elif broker_url.startswith("mqtts://"):
            host = broker_url.replace("mqtts://", "")
            port = 8883
        else:
            host = broker_url
            port = 1883

        if ":" in host and not host.startswith("["):
            host, port_str = host.rsplit(":", 1)
            port = int(port_str)

        return cls(
            broker_url=broker_url,
            port=port,
            client_id=settings.mqtt_client_id,
            keepalive=settings.mqtt_keepalive,
            clean_session=settings.mqtt_clean_session,
        )


class MQTTClient:
    """Async MQTT client wrapper."""

    def __init__(self, config: MQTTConfig):
        """Initialize MQTT client.

        Args:
            config: MQTT configuration
        """
        self.config = config
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=config.client_id,
            clean_session=config.clean_session,
            protocol=mqtt.MQTTv5
        )
        self._connected_event = asyncio.Event()
        self._disconnected_event = asyncio.Event()
        self._disconnected_event.set()  # Start as disconnected
        self._connection_retries = 0
        self._max_retries = 10
        self._retry_delay = 1.0
        self._subscriptions = {}
        self._message_callbacks = {}
        self._running = False
        self._connect_task = None
        self._logger = logger

    async def connect(self) -> bool:
        """Connect to MQTT broker.

        Returns:
            True if successful
        """
        try:
            # Set authentication if provided
            if self.config.username:
                self._client.username_pw_set(self.config.username, self.config.password)

            # Set TLS if certificates provided
            if self.config.ca_certs:
                self._client.tls_set(
                    ca_certs=self.config.ca_certs,
                    certfile=self.config.certfile,
                    keyfile=self.config.keyfile,
                )
                if self.config.tls_insecure:
                    self._client.tls_insecure_set(True)

            # Connect to broker
            self._logger.info("Connecting to MQTT broker", broker=self.config.broker_url)
            result_code = await asyncio.to_thread(
                self._client.connect,
                self.config.broker_url.replace("mqtt://", "").replace("mqtts://", ""),
                self.config.port,
                self.config.keepalive
            )

            if result_code == 0:
                self._connected_event.set()
                self._disconnected_event.clear()
                self._connection_retries = 0
                self._logger.info("Connected to MQTT broker")
                return True
            else:
                self._logger.error("Failed to connect to MQTT broker", code=result_code)
                return False

        except Exception as e:
            self._logger.error("Error connecting to MQTT broker", error=str(e))
            return False

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        self._running = False
        self._client.disconnect()
        self._connected_event.clear()
        self._disconnected_event.set()
        self._logger.info("Disconnected from MQTT broker")

    async def cycle(self) -> None:
        """Process message loop."""
        while self._running:
            try:
                self._client.loop(timeout=1.0)
                await asyncio.sleep(0.1)
            except Exception as e:
                self._logger.error("Error in message loop", error=str(e))
                if not self._connected_event.is_set():
                    await self._reconnect()
                await asyncio.sleep(1.0)

    async def _reconnect(self) -> bool:
        """Attempt to reconnect to broker.

        Returns:
            True if successful
        """
        if self._connection_retries >= self._max_retries:
            self._logger.error("Max reconnection attempts reached")
            return False

        self._connection_retries += 1
        delay = self._retry_delay * (2 ** (self._connection_retries - 1))
        self._logger.warning(
            "Attempting reconnection",
            attempt=self._connection_retries,
            max_attempts=self._max_retries,
            delay=delay
        )

        await asyncio.sleep(delay)
        return await self.connect()

    def on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        """Handle connection callback."""
        if reason_code == 0:
            self._connected_event.set()
            self._disconnected_event.clear()
            self._logger.info("Connected to MQTT broker")
            # Re-subscribe to topics
            for topic, callback in self._subscriptions.items():
                self.subscribe(topic, callback)
        else:
            self._logger.error("Connection failed", reason_code=reason_code)

    def on_disconnect(self, client, userdata, reason_code, properties) -> None:
        """Handle disconnection callback."""
        self._connected_event.clear()
        self._disconnected_event.set()
        self._logger.warning("Disconnected from MQTT broker", reason_code=reason_code)

    def on_message(self, client, userdata, message) -> None:
        """Handle incoming message callback."""
        try:
            payload = json.loads(message.payload.decode())
            topic = message.topic

            self._logger.debug("Received MQTT message", topic=topic)

            # Trigger callbacks
            if topic in self._message_callbacks:
                for callback in self._message_callbacks[topic]:
                    callback(payload)

            # Trigger subscription callbacks
            if topic in self._subscriptions:
                self._subscriptions[topic](payload)

        except json.JSONDecodeError as e:
            self._logger.error("Failed to decode MQTT message", error=str(e))
        except Exception as e:
            self._logger.error("Error processing MQTT message", error=str(e))

    async def subscribe(self, topic: str, callback: Callable[[dict], None]) -> bool:
        """Subscribe to a topic.

        Args:
            topic: Topic to subscribe to
            callback: Callback function for messages

        Returns:
            True if successful
        """
        try:
            result = await asyncio.to_thread(self._client.subscribe, topic)
            if result[0] == 0:
                self._subscriptions[topic] = callback
                self._logger.info("Subscribed to topic", topic=topic)
                return True
            return False
        except Exception as e:
            self._logger.error("Failed to subscribe to topic", topic=topic, error=str(e))
            return False

    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a topic.

        Args:
            topic: Topic to unsubscribe from

        Returns:
            True if successful
        """
        try:
            result = await asyncio.to_thread(self._client.unsubscribe, topic)
            if result[0] == 0:
                if topic in self._subscriptions:
                    del self._subscriptions[topic]
                self._logger.info("Unsubscribed from topic", topic=topic)
                return True
            return False
        except Exception as e:
            self._logger.error("Failed to unsubscribe from topic", topic=topic, error=str(e))
            return False

    async def publish(self, topic: str, payload: dict | str, qos: int = 1, retain: bool = False) -> bool:
        """Publish a message to a topic.

        Args:
            topic: Topic to publish to
            payload: Message payload
            qos: Quality of service level
            retain: Whether to retain the message

        Returns:
            True if successful
        """
        try:
            if isinstance(payload, dict):
                payload = json.dumps(payload)

            result = await asyncio.to_thread(
                self._client.publish,
                topic,
                payload,
                qos=qos,
                retain=retain
            )

            if result.rc == 0:
                self._logger.debug("Published message to topic", topic=topic, payload=payload[:100])
                return True
            return False
        except Exception as e:
            self._logger.error("Failed to publish message", topic=topic, error=str(e))
            return False

    async def publish_json(self, topic: str, payload: dict, qos: int = 1, retain: bool = False) -> bool:
        """Publish a JSON message.

        Args:
            topic: Topic to publish to
            payload: Dictionary payload
            qos: Quality of service level
            retain: Whether to retain the message

        Returns:
            True if successful
        """
        return await self.publish(topic, payload, qos, retain)

    async def publish_raw(self, topic: str, payload: bytes, qos: int = 1, retain: bool = False) -> bool:
        """Publish raw bytes.

        Args:
            topic: Topic to publish to
            payload: Raw bytes payload
            qos: Quality of service level
            retain: Whether to retain the message

        Returns:
            True if successful
        """
        try:
            result = await asyncio.to_thread(
                self._client.publish,
                topic,
                payload,
                qos=qos,
                retain=retain
            )
            return result.rc == 0
        except Exception as e:
            self._logger.error("Failed to publish raw message", topic=topic, error=str(e))
            return False

    async def start(self) -> None:
        """Start the MQTT client."""
        if self._running:
            return

        self._running = True
        self._client.on_connect = self.on_connect
        self._client.on_disconnect = self.on_disconnect
        self._client.on_message = self.on_message

        await self.connect()
        self._connect_task = asyncio.create_task(self.cycle())

    async def stop(self) -> None:
        """Stop the MQTT client."""
        self._running = False

        if self._connect_task:
            self._connect_task.cancel()
            try:
                await self._connect_task
            except asyncio.CancelledError:
                pass

        await self.disconnect()

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    @property
    def is_connected(self) -> bool:
        """Check if client is connected.

        Returns:
            True if connected
        """
        return self._connected_event.is_set()

    @property
    def client_id(self) -> str:
        """Get client ID.

        Returns:
            Client ID
        """
        return self.config.client_id