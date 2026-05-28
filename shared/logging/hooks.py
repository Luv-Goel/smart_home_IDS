import structlog
from typing import Optional
from shared.logging.tracing import set_correlation_id

logger = structlog.get_logger(__name__)


def log_mqtt_on_connect(client, userdata, flags, rc, properties=None):
    """
    Hook to log MQTT connection events.
    """
    # Set a new correlation ID for the connection flow
    set_correlation_id()

    if rc == 0:
        logger.info(
            "mqtt_connected",
            client_id=getattr(client, "_client_id", "unknown"),
            result_code=rc,
        )
    else:
        logger.error(
            "mqtt_connection_failed",
            client_id=getattr(client, "_client_id", "unknown"),
            result_code=rc,
        )


def log_mqtt_on_disconnect(client, userdata, rc):
    """
    Hook to log MQTT disconnection events.
    """
    set_correlation_id()
    logger.info(
        "mqtt_disconnected",
        client_id=getattr(client, "_client_id", "unknown"),
        result_code=rc,
        expected=rc == 0,
    )


def log_mqtt_on_message(client, userdata, msg):
    """
    Hook to log MQTT incoming messages.
    Should be called at the start of on_message handler.
    """
    # Try to extract correlation ID from payload if it's JSON,
    # but for this simple hook we just set a new one
    set_correlation_id()
    logger.debug(
        "mqtt_message_received",
        topic=msg.topic,
        qos=msg.qos,
        payload_size=len(msg.payload) if msg.payload else 0,
    )


class WebSocketLogger:
    """Helper for logging WebSocket lifecycle events."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.logger = structlog.get_logger("websocket").bind(client_id=client_id)

    def on_connect(self, client_ip: Optional[str] = None):
        set_correlation_id()
        self.logger.info("websocket_connected", client_ip=client_ip)

    def on_disconnect(self, code: int = 1000, reason: str = ""):
        set_correlation_id()
        self.logger.info("websocket_disconnected", close_code=code, reason=reason)

    def on_message(self, message_type: str, payload_size: int):
        set_correlation_id()
        self.logger.debug(
            "websocket_message_received",
            message_type=message_type,
            payload_size=payload_size,
        )

    def on_error(self, error: Exception):
        set_correlation_id()
        self.logger.error("websocket_error", exc_info=error)
