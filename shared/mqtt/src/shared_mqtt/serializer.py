import json
from typing import Any
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class MessageSerializer:
    """Utility to serialize and deserialize MQTT message payloads."""

    @staticmethod
    def serialize(payload: Any) -> bytes:
        """Serialize payload to bytes for MQTT publishing.
        Handles dicts, strings, and Pydantic models.
        """
        try:
            if isinstance(payload, bytes):
                return payload
            elif isinstance(payload, str):
                return payload.encode("utf-8")
            elif isinstance(payload, BaseModel):
                # Use model_dump_json in pydantic v2
                return payload.model_dump_json().encode("utf-8")
            elif isinstance(payload, dict) or isinstance(payload, list):
                return json.dumps(payload).encode("utf-8")
            else:
                return str(payload).encode("utf-8")
        except Exception as e:
            logger.error(
                "Failed to serialize payload", error=str(e), type=type(payload)
            )
            raise ValueError(f"Serialization failed: {e}")

    @staticmethod
    def deserialize(payload: bytes) -> Any:
        """Deserialize bytes from MQTT into Python objects (dict/string)."""
        try:
            decoded = payload.decode("utf-8")
            try:
                return json.loads(decoded)
            except json.JSONDecodeError:
                # If it's not valid JSON, return as string
                return decoded
        except Exception as e:
            logger.error("Failed to deserialize payload", error=str(e))
            # If we can't even decode utf-8, return raw bytes
            return payload
