"""MQTT topic registry and definitions for Smart Home IDS.

This module provides topic constants and registration utilities
for all MQTT communication within the IDS system.
"""

from enum import Enum
from typing import Callable


class MQTTHubTopic(str, Enum):
    """Hub topics for edge-to-cloud communication."""

    ALERTS = "ids/alerts"
    STATUS = "ids/status"
    CONFIG = "ids/config"
    COMMAND = "ids/command"
    HEARTBEAT = "ids/heartbeat"
    METRICS = "ids/metrics"
    LOGS = "ids/logs"
    BACKUP = "ids/backup"


class MQTTEdgeTopic(str, Enum):
    """Edge node topics."""

    # Alert topics
    ALERTS_CRITICAL = "ids/edge/{node_id}/alerts/critical"
    ALERTS_HIGH = "ids/edge/{node_id}/alerts/high"
    ALERTS_MEDIUM = "ids/edge/{node_id}/alerts/medium"
    ALERTS_LOW = "ids/edge/{node_id}/alerts/low"
    ALERTS_INFO = "ids/edge/{node_id}/alerts/info"

    # Status topics
    STATUS_HEALTH = "ids/edge/{node_id}/status/health"
    STATUS_COMPONENT = "ids/edge/{node_id}/status/component"
    STATUS_RESOURCE = "ids/edge/{node_id}/status/resource"

    # Data topics
    DATA_PACKETS = "ids/edge/{node_id}/data/packets"
    DATA_FEATURES = "ids/edge/{node_id}/data/features"
    DATA_INFERENCE = "ids/edge/{node_id}/data/inference"
    DATA_FLOW = "ids/edge/{node_id}/data/flow"

    # Control topics
    CONTROL_RESTART = "ids/edge/{node_id}/control/restart"
    CONTROL_UPDATE = "ids/edge/{node_id}/control/update"
    CONTROL_CONFIG = "ids/edge/{node_id}/control/config"

    # File topics
    FILE_MODEL = "ids/edge/{node_id}/file/model"
    FILE_LOG = "ids/edge/{node_id}/file/log"
    FILE_DUMP = "ids/edge/{node_id}/file/dump"


class TopicRegistry:
    """Registry for MQTT topics with utility methods."""

    def __init__(self):
        """Initialize topic registry."""
        self._topics = {}
        self._register_default_topics()
        self._topic_callbacks = {}

    def _register_default_topics(self):
        """Register default IDS topics."""
        self.register(MQTTHubTopic.ALERTS, "Alert notification topic")
        self.register(MQTTHubTopic.STATUS, "Status update topic")
        self.register(MQTTHubTopic.CONFIG, "Configuration update topic")
        self.register(MQTTHubTopic.COMMAND, "Command execution topic")
        self.register(MQTTHubTopic.HEARTBEAT, "Heartbeat topic")
        self.register(MQTTHubTopic.METRICS, "Metrics collection topic")
        self.register(MQTTHubTopic.LOGS, "Log aggregation topic")
        self.register(MQTTHubTopic.BACKUP, "Data backup topic")

    def register(self, topic: str, description: str = "") -> None:
        """Register a new topic.

        Args:
            topic: Topic string
            description: Optional description
        """
        self._topics[topic] = {
            "topic": topic,
            "description": description,
            "subscribers": [],
            "publishers": [],
        }

    def unregister(self, topic: str) -> bool:
        """Unregister a topic.

        Args:
            topic: Topic string

        Returns:
            True if topic was registered, False otherwise
        """
        if topic in self._topics:
            del self._topics[topic]
            return True
        return False

    def get_topic(self, topic: str) -> dict | None:
        """Get topic information.

        Args:
            topic: Topic string

        Returns:
            Topic information dictionary or None
        """
        return self._topics.get(topic)

    def list_topics(self) -> list[str]:
        """List all registered topics.

        Returns:
            List of topic strings
        """
        return list(self._topics.keys())

    def get_subscribers(self, topic: str) -> list[str]:
        """Get subscribers for a topic.

        Args:
            topic: Topic string

        Returns:
            List of subscriber IDs
        """
        topic_info = self._topics.get(topic)
        if topic_info:
            return topic_info.get("subscribers", [])
        return []

    def get_publishers(self, topic: str) -> list[str] | None:
        """Get publishers for a topic.

        Args:
            topic: Topic string

        Returns:
            List of publisher IDs or None
        """
        topic_info = self._topics.get(topic)
        if topic_info:
            return topic_info.get("publishers", [])
        return None

    def add_subscriber(self, topic: str, subscriber_id: str) -> bool:
        """Add a subscriber to a topic.

        Args:
            topic: Topic string
            subscriber_id: Subscriber identifier

        Returns:
            True if successful
        """
        topic_info = self._topics.get(topic)
        if topic_info and subscriber_id not in topic_info["subscribers"]:
            topic_info["subscribers"].append(subscriber_id)
            return True
        return False

    def remove_subscriber(self, topic: str, subscriber_id: str) -> bool:
        """Remove a subscriber from a topic.

        Args:
            topic: Topic topic string
            subscriber_id: Subscriber identifier

        Returns:
            True if successful
        """
        topic_info = self._topics.get(topic)
        if topic_info and subscriber_id in topic_info["subscribers"]:
            topic_info["subscribers"].remove(subscriber_id)
            return True
        return False

    def add_publisher(self, topic: str, publisher_id: str) -> bool:
        """Add a publisher to a topic.

        Args:
            topic: Topic string
            publisher_id: Publisher identifier

        Returns:
            True if successful
        """
        topic_info = self._topics.get(topic)
        if topic_info and publisher_id not in topic_info["publishers"]:
            topic_info["publishers"].append(publisher_id)
            return True
        return False

    def remove_publisher(self, topic: str, publisher_id: str) -> bool:
        """Remove a publisher from a topic.

        Args:
            topic: Topic string
            publisher_id: Publisher identifier

        Returns:
            True if successful
        """
        topic_info = self._topics.get(topic)
        if topic_info and publisher_id in topic_info["publishers"]:
            topic_info["publishers"].remove(publisher_id)
            return True
        return False

    def on_topic_message(self, topic: str, callback: Callable) -> None:
        """Register a callback for topic messages.

        Args:
            topic: Topic string
            callback: Callback function
        """
        if topic not in self._topic_callbacks:
            self._topic_callbacks[topic] = []
        self._topic_callbacks[topic].append(callback)

    def trigger_callbacks(self, topic: str, message: dict) -> None:
        """Trigger callbacks for a topic.

        Args:
            topic: Topic string
            message: Message payload
        """
        callbacks = self._topic_callbacks.get(topic, [])
        for callback in callbacks:
            callback(message)