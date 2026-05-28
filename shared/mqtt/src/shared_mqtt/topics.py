from enum import Enum
from typing import Dict, List, Optional


class IDSMQTTTopic(str, Enum):
    """Core MQTT topics for the IoT IDS system."""

    # Required topics per requirements
    ALERTS_CRITICAL = "ids/alerts/critical"
    ALERTS_WARNING = "ids/alerts/warning"
    DEVICES_DISCOVERED = "ids/devices/discovered"
    DEVICES_ANOMALOUS = "ids/devices/anomalous"
    FLOWS_ANOMALOUS = "ids/flows/anomalous"
    SYSTEM_HEALTH = "ids/system/health"
    INFERENCE_RESULTS = "ids/inference/results"
    THRESHOLDS_UPDATES = "ids/thresholds/updates"
    METRICS_SYSTEM = "ids/metrics/system"


class TopicBuilder:
    """Helper to dynamically build topic strings if needed."""

    @staticmethod
    def build_node_topic(base_topic: str, node_id: str) -> str:
        """Appends node_id to a base topic, e.g., for specific edge nodes."""
        return f"{base_topic}/{node_id}"


class TopicRegistry:
    """Registry for managing and introspecting registered topics."""

    def __init__(self):
        self._topics: Dict[str, str] = {}
        self._register_default_topics()

    def _register_default_topics(self) -> None:
        """Register all predefined topics."""
        for topic in IDSMQTTTopic:
            self.register(
                topic.value,
                f"Standard topic for {topic.name.lower().replace('_', ' ')}",
            )

    def register(self, topic: str, description: str = "") -> None:
        """Register a custom topic."""
        self._topics[topic] = description

    def unregister(self, topic: str) -> bool:
        """Remove a topic from the registry."""
        if topic in self._topics:
            del self._topics[topic]
            return True
        return False

    def list_topics(self) -> List[str]:
        """Get a list of all registered topics."""
        return list(self._topics.keys())

    def get_description(self, topic: str) -> Optional[str]:
        """Get the description for a topic."""
        return self._topics.get(topic)


# Singleton registry instance
registry = TopicRegistry()
