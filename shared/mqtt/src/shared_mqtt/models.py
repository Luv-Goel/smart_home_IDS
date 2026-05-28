from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from uuid import uuid4


class MQTTAuth(BaseModel):
    """Authentication configuration for MQTT."""

    username: Optional[str] = None
    password: Optional[str] = None


class MQTTTLSConfig(BaseModel):
    """TLS configuration for secure MQTT connections."""

    ca_certs: str = Field(description="Path to CA certificate file")
    certfile: Optional[str] = Field(
        default=None, description="Path to client certificate file"
    )
    keyfile: Optional[str] = Field(default=None, description="Path to client key file")
    insecure: bool = Field(
        default=False,
        description="Whether to disable certificate verification (use only in dev)",
    )


class MQTTConfig(BaseModel):
    """Main MQTT Configuration."""

    broker: str = Field(default="localhost", description="MQTT broker hostname or IP")
    port: int = Field(default=1883, description="MQTT broker port")
    client_id: str = Field(default_factory=lambda: f"ids-client-{uuid4().hex[:8]}")
    keepalive: int = Field(default=60, description="Keepalive interval in seconds")

    # Auth and TLS
    auth: Optional[MQTTAuth] = None
    tls: Optional[MQTTTLSConfig] = None

    # Reconnection behavior
    reconnect_min_delay: float = Field(
        default=1.0, description="Initial reconnect delay in seconds"
    )
    reconnect_max_delay: float = Field(
        default=60.0, description="Maximum reconnect delay in seconds"
    )
    max_reconnect_attempts: int = Field(
        default=0, description="Maximum reconnect attempts (0 = infinite)"
    )


class MQTTMessageData(BaseModel):
    """Generic payload structure for JSON messages over MQTT."""

    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    source_node: str = Field(default="unknown")
    payload: Any = Field(description="The actual data payload")
