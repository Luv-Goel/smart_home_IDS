import asyncio
import ssl
from typing import Callable, Dict, Any, Optional, Awaitable, List, cast
import structlog
from aiomqtt import Client, MqttError

from .models import MQTTConfig
from .serializer import MessageSerializer

logger = structlog.get_logger(__name__)

# Callback type: takes topic and deserialized payload
MessageCallback = Callable[[str, Any], Awaitable[None]]


class MQTTConnectionManager:
    """Manages the MQTT connection, publisher, and subscribers with auto-reconnect."""

    def __init__(self, config: MQTTConfig):
        self.config = config
        self._client: Optional[Client] = None
        self._connected = False
        self._running = False
        self._subscriptions: Dict[str, List[MessageCallback]] = {}
        self._bg_task: Optional[asyncio.Task] = None
        self._reconnect_delay = self.config.reconnect_min_delay

        # Build TLS Context if specified
        self._tls_context = None
        if self.config.tls:
            self._tls_context = ssl.create_default_context(
                cafile=self.config.tls.ca_certs
            )
            if self.config.tls.certfile and self.config.tls.keyfile:
                self._tls_context.load_cert_chain(
                    certfile=self.config.tls.certfile, keyfile=self.config.tls.keyfile
                )
            if self.config.tls.insecure:
                self._tls_context.check_hostname = False
                self._tls_context.verify_mode = ssl.CERT_NONE

    async def start(self) -> None:
        """Start the background connection loop."""
        if self._running:
            return

        self._running = True
        self._bg_task = asyncio.create_task(self._connection_loop())
        logger.info("MQTT Connection Manager started")

    async def stop(self) -> None:
        """Gracefully stop the connection manager."""
        self._running = False
        if self._bg_task:
            self._bg_task.cancel()
            try:
                await self._bg_task
            except asyncio.CancelledError:
                pass
        self._connected = False
        logger.info("MQTT Connection Manager stopped")

    async def _connection_loop(self) -> None:
        """Background loop handling connection and message listening."""
        auth_kwargs = {}
        if self.config.auth:
            auth_kwargs["username"] = self.config.auth.username
            auth_kwargs["password"] = self.config.auth.password

        attempt = 0
        while self._running:
            try:
                logger.info(
                    f"Connecting to MQTT broker at {self.config.broker}:{self.config.port}"
                )

                async with Client(
                    hostname=self.config.broker,
                    port=self.config.port,
                    identifier=self.config.client_id,
                    keepalive=self.config.keepalive,
                    tls_context=self._tls_context,
                    **cast(Any, auth_kwargs),
                ) as client:
                    self._client = client
                    self._connected = True
                    self._reconnect_delay = (
                        self.config.reconnect_min_delay
                    )  # reset backoff
                    attempt = 0

                    logger.info("Connected to MQTT broker")

                    # Resubscribe to existing topics
                    for topic in self._subscriptions.keys():
                        await client.subscribe(topic)
                        logger.debug(f"Resubscribed to {topic}")

                    # Listen for messages
                    async for message in client.messages:
                        topic_str = str(message.topic)
                        payload = MessageSerializer.deserialize(message.payload)

                        # Find matching callbacks
                        callbacks = []
                        for sub_topic, cbs in self._subscriptions.items():
                            if message.topic.matches(sub_topic):
                                callbacks.extend(cbs)

                        if callbacks:
                            for cb in callbacks:
                                # Run callbacks in background
                                asyncio.create_task(
                                    self._safe_invoke_callback(cb, topic_str, payload)
                                )

            except MqttError as e:
                self._connected = False
                self._client = None

                if not self._running:
                    break

                attempt += 1
                if (
                    self.config.max_reconnect_attempts > 0
                    and attempt > self.config.max_reconnect_attempts
                ):
                    logger.error(
                        f"Max reconnect attempts ({self.config.max_reconnect_attempts}) reached. Giving up."
                    )
                    self._running = False
                    break

                logger.warning(
                    f"MQTT connection error: {e}. Reconnecting in {self._reconnect_delay}s..."
                )
                await asyncio.sleep(self._reconnect_delay)

                # Exponential backoff
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self.config.reconnect_max_delay
                )

            except asyncio.CancelledError:
                self._connected = False
                logger.debug("Connection loop cancelled")
                break
            except Exception as e:
                self._connected = False
                logger.error(f"Unexpected error in connection loop: {e}")
                await asyncio.sleep(self._reconnect_delay)

    async def _safe_invoke_callback(
        self, callback: MessageCallback, topic: str, payload: Any
    ) -> None:
        """Safely invoke a message callback."""
        try:
            await callback(topic, payload)
        except Exception as e:
            logger.error(f"Error in message callback for topic {topic}", error=str(e))

    async def publish(
        self, topic: str, payload: Any, qos: int = 1, retain: bool = False
    ) -> bool:
        """Publish a message to a topic."""
        if not self._connected or not self._client:
            logger.warning("Cannot publish, not connected to broker")
            return False

        try:
            serialized_payload = MessageSerializer.serialize(payload)
            await self._client.publish(
                topic, payload=serialized_payload, qos=qos, retain=retain
            )
            logger.debug(f"Published to {topic}")
            return True
        except MqttError as e:
            logger.error(f"Failed to publish to {topic}", error=str(e))
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing to {topic}", error=str(e))
            return False

    async def subscribe(self, topic: str, callback: MessageCallback) -> bool:
        """Subscribe to a topic and register a callback."""
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []

        self._subscriptions[topic].append(callback)

        # If already connected, send the subscribe command immediately
        if self._connected and self._client:
            try:
                await self._client.subscribe(topic)
                logger.debug(f"Subscribed to {topic}")
                return True
            except MqttError as e:
                logger.error(f"Failed to subscribe to {topic}", error=str(e))
                return False

        # If not connected, it will be subscribed upon connection
        return True

    async def unsubscribe(
        self, topic: str, callback: Optional[MessageCallback] = None
    ) -> bool:
        """Unsubscribe from a topic. If callback is provided, removes only that callback."""
        if topic not in self._subscriptions:
            return True

        if callback:
            if callback in self._subscriptions[topic]:
                self._subscriptions[topic].remove(callback)

            # If there are still callbacks for this topic, don't unsubscribe from the broker
            if self._subscriptions[topic]:
                return True

        # Remove topic entirely if no callback specified or list is empty
        del self._subscriptions[topic]

        if self._connected and self._client:
            try:
                await self._client.unsubscribe(topic)
                logger.debug(f"Unsubscribed from {topic}")
                return True
            except MqttError as e:
                logger.error(f"Failed to unsubscribe from {topic}", error=str(e))
                return False

        return True

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()
        # Wait briefly to allow connection to establish
        # In a real app we might want to wait for the _connected flag explicitly
        await asyncio.sleep(0.1)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
